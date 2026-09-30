"""CLIエントリポイントモジュール.

pip install zabbix-googlechat でインストール後、
zabbix-googlechat-notify コマンドとして利用可能になる。

呼び出し形式:
    zabbix-googlechat-notify {ALERT.SENDTO} {ALERT.SUBJECT} {ALERT.MESSAGE}

設定ファイル探索順序:
    1. 環境変数 ZABBIX_GOOGLECHAT_CONFIG で明示指定
    2. /etc/zabbix-googlechat/config.yaml（FHS標準パス）
    3. カレントディレクトリの config/config.yaml
    4. 設定ファイルなし（環境変数のみで動作）

終了コード:
    0: 成功
    1: 設定エラー（ConfigurationError）
    2: 送信エラー（WebhookConnectionError, WebhookPayloadError）
    3: パースエラー（ParseError）
    99: 予期しないエラー
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from zabbix_googlechat.card_builder import build_payload
from zabbix_googlechat.config import NotificationConfig
from zabbix_googlechat.exceptions import (
    ConfigurationError,
    ParseError,
    WebhookConnectionError,
    WebhookPayloadError,
)
from zabbix_googlechat.models import AlertType, CardStyle, ZabbixEvent
from zabbix_googlechat.parser import ZabbixParamParser
from zabbix_googlechat.webhook_sender import GoogleChatWebhookSender, WebhookResponse

# 終了コード定数
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_SEND_ERROR = 2
EXIT_PARSE_ERROR = 3
EXIT_UNEXPECTED_ERROR = 99

# 設定ファイルパスを環境変数で指定する場合の環境変数名
_ENV_CONFIG_PATH = "ZABBIX_GOOGLECHAT_CONFIG"

# FHS標準設定ファイルパス
_FHS_CONFIG_PATH = Path("/etc/zabbix-googlechat/config.yaml")

# カレントディレクトリ相対パス
_LOCAL_CONFIG_PATH = Path("config/config.yaml")


def _find_config_path() -> Path | None:
    """設定ファイルのパスを探索する.

    探索順序:
        1. 環境変数 ZABBIX_GOOGLECHAT_CONFIG で明示指定
        2. /etc/zabbix-googlechat/config.yaml（FHS標準パス）
        3. カレントディレクトリの config/config.yaml
        4. 設定ファイルなし（環境変数のみで動作）

    Returns:
        見つかった設定ファイルのパス、または None
    """
    logger = logging.getLogger(__name__)

    # 1. 環境変数で明示指定
    env_path = os.environ.get(_ENV_CONFIG_PATH, "")
    if env_path:
        config_path = Path(env_path)
        if config_path.exists():
            logger.debug("設定ファイル（環境変数指定）: %s", config_path)
            return config_path
        # 環境変数で指定されたパスが存在しない場合は警告して None を返す
        logger.warning("%s で指定されたファイルが見つかりません: %s", _ENV_CONFIG_PATH, env_path)
        return None

    # 2. FHS標準パス
    if _FHS_CONFIG_PATH.exists():
        logger.debug("設定ファイル（FHS標準パス）: %s", _FHS_CONFIG_PATH)
        return _FHS_CONFIG_PATH

    # 3. カレントディレクトリの config/config.yaml
    if _LOCAL_CONFIG_PATH.exists():
        logger.debug("設定ファイル（ローカル）: %s", _LOCAL_CONFIG_PATH)
        return _LOCAL_CONFIG_PATH

    # 4. 設定ファイルなし（環境変数のみで動作）
    logger.debug("設定ファイルなし: 環境変数のみで動作")
    return None


def setup_logging(config: NotificationConfig) -> None:
    """ロギングを設定する.

    Args:
        config: 通知設定（log_level, log_file を参照）
    """
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if config.log_file:
        try:
            file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
            handlers.append(file_handler)
        except OSError as e:
            print(
                f"警告: ログファイルを開けません ({e})、標準エラーのみ使用",
                file=sys.stderr,
            )

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,  # 既存のハンドラを上書きして再設定
    )


def _send_via_api(
    config: NotificationConfig, event: ZabbixEvent, payload: dict[str, Any]
) -> WebhookResponse:
    """Chat API で送信する.

    PROBLEM はイベントIDから決まるメッセージIDを付けて投稿し、RECOVERY は同じIDの
    メッセージを復旧内容で置き換える（障害メッセージが無ければ新規投稿になる）。
    UPDATE（確認・コメント）は新しいメッセージとして投稿する。

    Raises:
        ConfigurationError: サービスアカウント鍵を読み込めない場合
    """
    # google-auth は Chat API を使う場合だけ読み込む
    # （Python 3.9 では import 時に FutureWarning を出すため、Webhook 利用時に出さない）
    from zabbix_googlechat.chat_api_sender import GoogleChatApiSender, build_message_id

    logger = logging.getLogger(__name__)
    message_id = build_message_id(config.message_id_prefix, event.event_id)
    if message_id is None and event.alert_type in (AlertType.PROBLEM, AlertType.RECOVERY):
        logger.warning(
            "EVENT_ID '%s' からメッセージIDを作れないため、復旧時の更新は行わず新規投稿します",
            event.event_id,
        )

    with GoogleChatApiSender(
        space=config.space,
        credentials_file=config.credentials_file,
        timeout=config.timeout,
        max_retries=config.max_retries,
        retry_delay=config.retry_delay,
    ) as sender:
        if event.alert_type == AlertType.RECOVERY and message_id is not None:
            return sender.upsert(payload, message_id)
        if event.alert_type == AlertType.PROBLEM:
            return sender.create(payload, message_id)
        return sender.create(payload, None)


def _send_via_webhook(config: NotificationConfig, payload: dict[str, Any]) -> WebhookResponse:
    """Webhook で送信する."""
    with GoogleChatWebhookSender(
        webhook_url=config.webhook_url,
        timeout=config.timeout,
        max_retries=config.max_retries,
        retry_delay=config.retry_delay,
    ) as sender:
        return sender.send(payload)


def main() -> int:
    """メイン処理.

    Returns:
        終了コード
    """
    # 基本ロギング設定（設定ファイル読込前）
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger(__name__)

    # 1. パラメータパース
    try:
        parser = ZabbixParamParser()
        event = parser.parse_argv(sys.argv[1:])
        logger.debug(
            "パース完了: alert_type=%s, host=%s, trigger=%s",
            event.alert_type,
            event.host_name,
            event.trigger_name,
        )
    except ParseError as e:
        print(f"パースエラー: {e}", file=sys.stderr)
        return EXIT_PARSE_ERROR

    # 2. 設定読込
    try:
        yaml_path = _find_config_path()
        config = NotificationConfig.load(
            yaml_path=yaml_path,
            alert_sendto=event.webhook_url,
        )
        # イベントのzabbix_urlが空の場合、設定ファイルのURLで補完
        if not event.zabbix_url and config.zabbix_url:
            event.zabbix_url = config.zabbix_url

        config.validate()
        logger.debug("設定読込完了: timeout=%d, max_retries=%d", config.timeout, config.max_retries)
    except ConfigurationError as e:
        print(f"設定エラー: {e}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    # ロギング再設定（設定ファイルのログレベルを適用）
    setup_logging(config)
    logger = logging.getLogger(__name__)

    # 3. カードビルド
    # スタイル優先順位: アクション本文の CARD_STYLE > 設定ファイル/環境変数 > 既定(detailed)
    # アクション本文の値が不正な場合は、設定ファイルで検証済みの値へフォールバックする
    # （タイプミスで意図せず detailed に落ちるのを防ぐ）。
    known_styles = {style.value for style in CardStyle}
    if event.card_style and event.card_style in known_styles:
        effective_style = event.card_style
    else:
        if event.card_style:
            logger.warning(
                "メッセージ本文の CARD_STYLE '%s' が不正です。設定ファイルの '%s' を使用します",
                event.card_style,
                config.card_style,
            )
        effective_style = config.card_style
    payload = build_payload(event, effective_style)
    logger.debug("カードビルド完了: style=%s", effective_style)

    # 4. 送信（space が設定されていれば Chat API、それ以外は Webhook）
    try:
        if config.space:
            response = _send_via_api(config, event, payload)
        else:
            response = _send_via_webhook(config, payload)

        if not response.success:
            logger.error("送信失敗: %s (status=%d)", response.error_message, response.status_code)
            print(f"送信エラー (HTTP {response.status_code}): {response.body}", file=sys.stderr)
            return EXIT_SEND_ERROR

        logger.info(
            "通知送信完了: host=%s, trigger=%s, retry=%d, elapsed=%.1fms",
            event.host_name,
            event.trigger_name,
            response.retry_count,
            response.elapsed_ms,
        )
        return EXIT_SUCCESS

    except ConfigurationError as e:
        logger.error("設定エラー: %s", e)
        print(f"設定エラー: {e}", file=sys.stderr)
        return EXIT_CONFIG_ERROR

    except WebhookPayloadError as e:
        logger.error("Webhookペイロードエラー: %s (status=%d)", e, e.status_code)
        print(f"送信エラー (HTTP {e.status_code}): {e}", file=sys.stderr)
        return EXIT_SEND_ERROR

    except WebhookConnectionError as e:
        logger.error("Webhook接続エラー: %s (retry=%d)", e, e.retry_count)
        print(f"送信エラー (接続失敗): {e}", file=sys.stderr)
        return EXIT_SEND_ERROR

    except Exception as e:  # noqa: BLE001
        logger.exception("予期しないエラー: %s", e)
        print(f"予期しないエラー: {e}", file=sys.stderr)
        return EXIT_UNEXPECTED_ERROR


if __name__ == "__main__":
    sys.exit(main())
