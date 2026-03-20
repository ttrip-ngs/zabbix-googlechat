#!/usr/bin/env python3
"""Zabbix 外部スクリプト エントリポイント.

呼び出し形式:
    zabbix_notify.py {ALERT.SENDTO} {ALERT.SUBJECT} {ALERT.MESSAGE}

終了コード:
    0: 成功
    1: 設定エラー（ConfigurationError）
    2: 送信エラー（WebhookConnectionError, WebhookPayloadError）
    3: パースエラー（ParseError）
    99: 予期しないエラー
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加（スクリプト直接実行時）
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_SRC_DIR = _PROJECT_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from zabbix_googlechat.card_builder import GoogleChatCardBuilder  # noqa: E402
from zabbix_googlechat.config import NotificationConfig  # noqa: E402
from zabbix_googlechat.exceptions import (  # noqa: E402
    ConfigurationError,
    ParseError,
    WebhookConnectionError,
    WebhookPayloadError,
)
from zabbix_googlechat.parser import ZabbixParamParser  # noqa: E402
from zabbix_googlechat.webhook_sender import GoogleChatWebhookSender  # noqa: E402

# 終了コード定数
EXIT_SUCCESS = 0
EXIT_CONFIG_ERROR = 1
EXIT_SEND_ERROR = 2
EXIT_PARSE_ERROR = 3
EXIT_UNEXPECTED_ERROR = 99

# デフォルトの設定ファイルパス
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"


def setup_logging(config: NotificationConfig) -> None:
    """ロギングを設定する."""
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]

    if config.log_file:
        try:
            file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
            handlers.append(file_handler)
        except OSError as e:
            print(f"警告: ログファイルを開けません ({e})、標準エラーのみ使用", file=sys.stderr)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


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
        yaml_path = _DEFAULT_CONFIG_PATH if _DEFAULT_CONFIG_PATH.exists() else None
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
    builder = GoogleChatCardBuilder(event)
    payload = builder.build()
    logger.debug("カードビルド完了: card_id=%s", payload.get("cardsV2", [{}])[0].get("cardId", ""))

    # 4. Webhook送信
    try:
        with GoogleChatWebhookSender(
            webhook_url=config.webhook_url,
            timeout=config.timeout,
            max_retries=config.max_retries,
            retry_delay=config.retry_delay,
        ) as sender:
            response = sender.send(payload)

        logger.info(
            "通知送信完了: host=%s, trigger=%s, retry=%d, elapsed=%.1fms",
            event.host_name,
            event.trigger_name,
            response.retry_count,
            response.elapsed_ms,
        )
        return EXIT_SUCCESS

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
