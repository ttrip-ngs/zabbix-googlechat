"""Google Chat Webhook 送信クライアント."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, TypeVar

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import RequestException, Timeout

from zabbix_googlechat.exceptions import WebhookConnectionError, WebhookPayloadError

logger = logging.getLogger(__name__)

# リトライ対象のHTTPステータスコード
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# クライアントエラー（リトライ不要）
_CLIENT_ERROR_STATUS_CODES = {400, 401, 403, 404}

_SenderT = TypeVar("_SenderT", bound="_RetryingSender")


@dataclass
class WebhookResponse:
    """Webhook送信レスポンス."""

    success: bool
    status_code: int
    body: str
    retry_count: int = 0
    elapsed_ms: float = 0.0
    error_message: str = ""


class _RetryingSender:
    """リトライ付きで Google Chat へ HTTP リクエストを送る共通基底クラス.

    リトライ戦略:
        - 対象: 429 / 500 / 502 / 503 / 504 およびネットワーク障害
        - 非対象: 400 / 401 / 403 / 404 などのクライアントエラー
        - バックオフ: 指数バックオフ（retry_delay * 2^retry_count）
    """

    # ネットワーク障害としてリトライする例外（サブクラスで追加可能）
    _retryable_errors: tuple[type[Exception], ...] = (
        RequestsConnectionError,
        ConnectionError,
        Timeout,
    )

    # 呼び出し側で処理する想定内の HTTP ステータス（success=False で返し、ERROR ログを出さない）
    _expected_statuses: frozenset[int] = frozenset()

    def __init__(
        self,
        session: requests.Session,
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """初期化.

        Args:
            session: 送信に使う HTTP セッション
            timeout: HTTPリクエストタイムアウト（秒）
            max_retries: 最大リトライ回数（0=リトライなし）
            retry_delay: リトライ間隔基準値（秒）
        """
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._session = session
        self._session.headers.update({"Content-Type": "application/json; charset=UTF-8"})

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any],
        params: dict[str, str] | None = None,
    ) -> WebhookResponse:
        """ペイロードをリトライ付きで送信する.

        Args:
            method: HTTPメソッド（POST / PATCH）
            url: 送信先URL
            payload: 送信するJSONペイロード
            params: クエリパラメータ

        Returns:
            WebhookResponse

        Raises:
            WebhookPayloadError: 400 Bad Request など修正不可能なエラー
            WebhookConnectionError: リトライ上限超過後もネットワーク障害継続
        """
        retry_count = 0
        last_error: Exception | None = None
        start_time = time.monotonic()

        while retry_count <= self._max_retries:
            if retry_count > 0:
                delay = self._retry_delay * (2 ** (retry_count - 1))
                logger.info(
                    "リトライ待機 %.1f秒 (%d/%d回目)", delay, retry_count, self._max_retries
                )
                time.sleep(delay)

            try:
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    json=payload,
                    timeout=self._timeout,
                )
                elapsed_ms = (time.monotonic() - start_time) * 1000

                logger.debug(
                    "送信レスポンス: status=%d, elapsed=%.1fms",
                    response.status_code,
                    elapsed_ms,
                )

                # クライアントエラー（リトライ不要）
                if response.status_code in _CLIENT_ERROR_STATUS_CODES:
                    raise WebhookPayloadError(
                        f"Webhookペイロードエラー: HTTP {response.status_code}",
                        status_code=response.status_code,
                        response_body=response.text,
                    )

                # 成功
                if response.status_code == 200:  # noqa: PLR2004
                    logger.info(
                        "送信成功: status=%d, elapsed=%.1fms, retry=%d",
                        response.status_code,
                        elapsed_ms,
                        retry_count,
                    )
                    return WebhookResponse(
                        success=True,
                        status_code=response.status_code,
                        body=response.text,
                        retry_count=retry_count,
                        elapsed_ms=elapsed_ms,
                    )

                # サーバーエラー（リトライ対象）
                if response.status_code in _RETRYABLE_STATUS_CODES:
                    logger.warning(
                        "送信失敗（リトライ対象）: HTTP %d, retry=%d/%d",
                        response.status_code,
                        retry_count,
                        self._max_retries,
                    )
                    last_error = WebhookConnectionError(
                        f"HTTP {response.status_code}",
                        retry_count=retry_count,
                    )
                    retry_count += 1
                    continue

                # その他のエラー
                if response.status_code in self._expected_statuses:
                    logger.debug("HTTPステータス %d を呼び出し側で処理", response.status_code)
                else:
                    logger.error("予期しないHTTPステータス: %d", response.status_code)
                return WebhookResponse(
                    success=False,
                    status_code=response.status_code,
                    body=response.text,
                    retry_count=retry_count,
                    elapsed_ms=(time.monotonic() - start_time) * 1000,
                    error_message=f"予期しないHTTPステータス: {response.status_code}",
                )

            except WebhookPayloadError:
                raise

            except self._retryable_errors as e:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                logger.warning(
                    "接続エラー: %s, retry=%d/%d",
                    e,
                    retry_count,
                    self._max_retries,
                )
                last_error = e
                retry_count += 1
                continue

            except RequestException as e:
                elapsed_ms = (time.monotonic() - start_time) * 1000
                logger.error("送信リクエストエラー: %s", e)
                raise WebhookConnectionError(
                    f"Webhookリクエストエラー: {e}",
                    retry_count=retry_count,
                ) from e

        # リトライ上限超過
        elapsed_ms = (time.monotonic() - start_time) * 1000
        error_msg = f"リトライ上限({self._max_retries}回)超過: {last_error}"
        logger.error(error_msg)
        raise WebhookConnectionError(error_msg, retry_count=retry_count - 1)

    def close(self) -> None:
        """HTTPセッションをクローズする."""
        self._session.close()

    def __enter__(self: _SenderT) -> _SenderT:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class GoogleChatWebhookSender(_RetryingSender):
    """Google Chat Webhook 送信クライアント（新規投稿のみ。投稿済みメッセージは更新できない）."""

    def __init__(
        self,
        webhook_url: str,
        timeout: int = 10,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """初期化.

        Args:
            webhook_url: Google Chat Webhook URL
            timeout: HTTPリクエストタイムアウト（秒）
            max_retries: 最大リトライ回数（0=リトライなし）
            retry_delay: リトライ間隔基準値（秒）
        """
        super().__init__(requests.Session(), timeout, max_retries, retry_delay)
        self._webhook_url = webhook_url

    def send(self, payload: dict[str, Any]) -> WebhookResponse:
        """Google Chat にペイロードを送信する.

        Args:
            payload: 送信するJSONペイロード

        Returns:
            WebhookResponse

        Raises:
            WebhookPayloadError: 400 Bad Request など修正不可能なエラー
            WebhookConnectionError: リトライ上限超過後もネットワーク障害継続
        """
        return self._request("POST", self._webhook_url, payload)
