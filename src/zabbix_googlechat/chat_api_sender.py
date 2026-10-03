"""Google Chat API 送信クライアント（Chat アプリ + サービスアカウント認証）.

Webhook では投稿済みメッセージを更新できない。Chat API のアプリ認証なら、
同じ Chat アプリが投稿したメッセージを更新できる。

障害発生時のメッセージにはクライアント指定のメッセージID（client-<prefix>-<EVENT.ID>）を
付けて投稿する。復旧時は同じIDでメッセージを更新するため、メッセージ名を保存しておく
必要がない。
"""

from __future__ import annotations

import logging
import re
from typing import Any

from google.auth.exceptions import GoogleAuthError, RefreshError, TransportError
from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

from zabbix_googlechat.exceptions import ConfigurationError, WebhookPayloadError
from zabbix_googlechat.webhook_sender import WebhookResponse, _RetryingSender

logger = logging.getLogger(__name__)

_API_BASE_URL = "https://chat.googleapis.com/v1"

# Chat アプリとして認証するスコープ
_CHAT_BOT_SCOPE = "https://www.googleapis.com/auth/chat.bot"

# 同じメッセージIDが既に存在する（エスカレーションによる再通知など）
_HTTP_CONFLICT = 409
_HTTP_BAD_REQUEST = 400

# 更新に失敗した場合に新規投稿へ切り替えるステータス
# （別の Chat アプリが作成したメッセージ、更新形式の拒否など。通知を失わないため）
_UPSERT_FALLBACK_STATUSES = {400, 403, 404}

# 更新対象フィールド。スタイル変更（カード ⇔ テキスト）にも対応するため両方を指定し、
# ペイロードに無い方は空になる
_UPDATE_MASK = "text,cardsV2"

# クライアント指定メッセージIDの形式（Chat API の制約: client- で始まり、英小文字・数字・
# ハイフンのみ、63文字以内）
_MESSAGE_ID_PATTERN = re.compile(r"client-[a-z0-9-]+")
_MESSAGE_ID_MAX_LENGTH = 63


def build_message_id(prefix: str, event_id: str) -> str | None:
    """Zabbix のイベントIDからクライアント指定メッセージIDを組み立てる.

    Args:
        prefix: メッセージIDの接頭辞（同じスペースに複数の Zabbix が投稿する場合に区別する）
        event_id: 障害イベントID（復旧時も {EVENT.ID} は障害イベントのIDになる）

    Returns:
        メッセージID。イベントIDが数字でない場合は None（IDなしで新規投稿する）
    """
    if not event_id.isdigit():
        return None
    message_id = f"client-{prefix}-{event_id}"
    if len(message_id) > _MESSAGE_ID_MAX_LENGTH or not _MESSAGE_ID_PATTERN.fullmatch(message_id):
        return None
    return message_id


class GoogleChatApiSender(_RetryingSender):
    """Google Chat API 送信クライアント.

    Chat アプリを対象スペースに追加しておく必要がある。
    """

    # アクセストークン取得時のネットワーク障害もリトライする
    _retryable_errors = (*_RetryingSender._retryable_errors, TransportError)

    # 同じメッセージIDが既に存在する場合は create() でIDなしの投稿に切り替える
    _expected_statuses = frozenset({_HTTP_CONFLICT})

    def __init__(
        self,
        space: str,
        credentials_file: str,
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """初期化.

        Args:
            space: 送信先スペース名（spaces/XXXXXXXX）
            credentials_file: サービスアカウント鍵（JSON）のパス
            timeout: HTTPリクエストタイムアウト（秒）
            max_retries: 最大リトライ回数（0=リトライなし）
            retry_delay: リトライ間隔基準値（秒）

        Raises:
            ConfigurationError: サービスアカウント鍵を読み込めない場合
        """
        try:
            credentials = service_account.Credentials.from_service_account_file(
                credentials_file, scopes=[_CHAT_BOT_SCOPE]
            )
        except (OSError, ValueError, GoogleAuthError) as e:
            raise ConfigurationError(
                f"サービスアカウント鍵を読み込めません: {credentials_file} ({e})"
            ) from e

        super().__init__(AuthorizedSession(credentials), timeout, max_retries, retry_delay)
        self._messages_url = f"{_API_BASE_URL}/{space}/messages"

    def create(self, payload: dict[str, Any], message_id: str | None) -> WebhookResponse:
        """メッセージを新規投稿する.

        同じメッセージIDが既に存在する場合（エスカレーションで同じ障害を再通知した場合など）は、
        IDなしの新しいメッセージとして投稿する。

        Args:
            payload: 送信するJSONペイロード
            message_id: クライアント指定メッセージID（None の場合はIDなし）

        Returns:
            WebhookResponse
        """
        if message_id is None:
            return self._send("POST", self._messages_url, payload)

        try:
            response = self._send("POST", self._messages_url, payload, {"messageId": message_id})
        except WebhookPayloadError as e:
            # ID重複のエラーは 409 の想定だが、400 で返る場合にも通知を失わないようにする
            # （ペイロード自体の誤りなら、IDなしの投稿も同じエラーになる）
            if e.status_code != _HTTP_BAD_REQUEST:
                raise
            logger.warning(
                "メッセージID %s 付きの投稿が HTTP 400 のため、IDなしで投稿します", message_id
            )
            return self._send("POST", self._messages_url, payload)

        if response.status_code == _HTTP_CONFLICT:
            logger.info(
                "メッセージID %s は投稿済みのため、新しいメッセージとして投稿します", message_id
            )
            return self._send("POST", self._messages_url, payload)
        return response

    def upsert(self, payload: dict[str, Any], message_id: str) -> WebhookResponse:
        """メッセージを更新する。対象が無い場合は同じIDで新規投稿する.

        更新が恒久エラー（400 / 403 / 404）になった場合は、IDなしの新しいメッセージとして投稿する。

        Args:
            payload: 送信するJSONペイロード
            message_id: クライアント指定メッセージID

        Returns:
            WebhookResponse
        """
        try:
            return self._send(
                "PATCH",
                f"{self._messages_url}/{message_id}",
                payload,
                {"updateMask": _UPDATE_MASK, "allowMissing": "true"},
            )
        except WebhookPayloadError as e:
            if e.status_code not in _UPSERT_FALLBACK_STATUSES:
                raise
            logger.warning(
                "メッセージ %s の更新が HTTP %d のため、新しいメッセージとして投稿します",
                message_id,
                e.status_code,
            )
            return self._send("POST", self._messages_url, payload)

    def _send(
        self,
        method: str,
        url: str,
        payload: dict[str, Any],
        params: dict[str, str] | None = None,
    ) -> WebhookResponse:
        """認証エラーを送信エラーに変換して送信する."""
        try:
            return self._request(method, url, payload, params)
        except RefreshError as e:
            raise WebhookPayloadError(
                f"アクセストークンを取得できません（サービスアカウント鍵を確認してください）: {e}",
                status_code=401,
            ) from e
