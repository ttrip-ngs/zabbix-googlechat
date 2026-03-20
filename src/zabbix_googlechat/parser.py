"""Zabbix アラートパラメータのパーサー."""

from __future__ import annotations

import logging
import sys
from collections.abc import Sequence

from zabbix_googlechat.exceptions import ParseError
from zabbix_googlechat.models import AlertType, Severity, ZabbixEvent

logger = logging.getLogger(__name__)

# Zabbixメッセージ本文のキーマッピング
# キー名（大文字）→ ZabbixEventフィールド名
_KEY_MAP: dict[str, str] = {
    "ALERT_TYPE": "alert_type",
    "HOST_NAME": "host_name",
    "TRIGGER_NAME": "trigger_name",
    "TRIGGER_DESCRIPTION": "trigger_description",
    "TRIGGER_SEVERITY": "trigger_severity",
    "EVENT_ID": "event_id",
    "EVENT_DATE": "event_date",
    "EVENT_TIME": "event_time",
    "RECOVERY_DATE": "recovery_date",
    "RECOVERY_TIME": "recovery_time",
    "ACK_MESSAGE": "ack_message",
    "ACK_AUTHOR": "ack_author",
    "ITEM_LASTVALUE": "item_last_value",
    "ZABBIX_URL": "zabbix_url",
}


class ZabbixParamParser:
    """Zabbixパラメータのパーサー.

    Zabbixの外部スクリプト呼び出し形式:
        zabbix_notify.py {ALERT.SENDTO} {ALERT.SUBJECT} {ALERT.MESSAGE}

    メッセージ本文 ({ALERT.MESSAGE}) は改行区切りの key=value 形式:
        ALERT_TYPE=PROBLEM
        HOST_NAME=web01.example.com
        TRIGGER_NAME=CPU使用率が高い
        ...
    """

    def parse_argv(self, argv: Sequence[str] | None = None) -> ZabbixEvent:
        """sys.argv から ZabbixEvent を構築する.

        Args:
            argv: コマンドライン引数リスト（None の場合 sys.argv を使用）

        Returns:
            パースされた ZabbixEvent

        Raises:
            ParseError: 必須引数が不足している場合
        """
        args = list(argv) if argv is not None else sys.argv[1:]

        if len(args) < 3:  # noqa: PLR2004
            raise ParseError(
                f"引数が不足しています。必要: 3個、受取: {len(args)}個\n"
                "使用方法: zabbix_notify.py {ALERT.SENDTO} {ALERT.SUBJECT} {ALERT.MESSAGE}"
            )

        webhook_url = args[0].strip()
        # args[1] は {ALERT.SUBJECT}（現在は使用しないが将来拡張のため保持）
        message_body = args[2]

        event = self.parse_message_body(message_body)
        event.raw_message = message_body

        # webhook_urlが空でない場合のみ上書き（config優先のため、空文字は無視）
        if webhook_url:
            event.webhook_url = webhook_url

        return event

    def parse_message_body(self, message: str) -> ZabbixEvent:
        """改行区切り key=value 形式のメッセージ本文をパースする.

        Args:
            message: Zabbixメッセージ本文

        Returns:
            パースされた ZabbixEvent
        """
        parsed: dict[str, str] = {}
        extra: dict[str, str] = {}

        for line in message.splitlines():
            line = line.strip()
            if not line:
                continue

            if "=" not in line:
                logger.debug("キーバリュー形式でない行をスキップ: %s", line)
                continue

            # 最初の = でのみ分割（値にも = が含まれる可能性あり）
            key, _, value = line.partition("=")
            key = key.strip().upper()
            value = value.strip()

            if key in _KEY_MAP:
                parsed[_KEY_MAP[key]] = value
            else:
                extra[key] = value
                logger.debug("未知のキー: %s = %s", key, value)

        # ZabbixEvent を構築
        event = ZabbixEvent(extra=extra)

        # alert_type
        raw_alert_type = parsed.get("alert_type", "")
        event.alert_type = self._normalize_alert_type(raw_alert_type)

        # trigger_severity
        raw_severity = parsed.get("trigger_severity", "")
        event.trigger_severity = self._normalize_severity(raw_severity)

        # その他のフィールドをセット
        for field_name in [
            "host_name",
            "trigger_name",
            "trigger_description",
            "event_id",
            "event_date",
            "event_time",
            "recovery_date",
            "recovery_time",
            "ack_message",
            "ack_author",
            "item_last_value",
            "zabbix_url",
        ]:
            if field_name in parsed:
                setattr(event, field_name, parsed[field_name])

        return event

    def _normalize_alert_type(self, raw: str) -> AlertType:
        """文字列を AlertType に変換する（不明値は UPDATE にフォールバック）."""
        normalized = raw.strip().upper()
        for alert_type in AlertType:
            if alert_type.value == normalized:
                return alert_type
        if normalized:
            logger.warning("不明なアラートタイプ '%s'、UPDATE にフォールバック", raw)
        return AlertType.UPDATE

    def _normalize_severity(self, raw: str) -> Severity:
        """文字列を Severity に変換する（不明値は NOT_CLASSIFIED にフォールバック）."""
        normalized = raw.strip()
        # 大文字小文字を区別しない比較
        for severity in Severity:
            if severity.value.lower() == normalized.lower():
                return severity
        if normalized:
            logger.warning("不明な重要度 '%s'、NOT_CLASSIFIED にフォールバック", raw)
        return Severity.NOT_CLASSIFIED
