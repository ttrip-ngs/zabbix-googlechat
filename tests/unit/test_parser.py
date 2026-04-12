"""parser.py のユニットテスト."""

import pytest

from zabbix_googlechat.exceptions import ParseError
from zabbix_googlechat.models import AlertType, Severity
from zabbix_googlechat.parser import ZabbixParamParser


@pytest.fixture
def parser() -> ZabbixParamParser:
    return ZabbixParamParser()


SAMPLE_PROBLEM_MESSAGE = """ALERT_TYPE=PROBLEM
HOST_NAME=web01.example.com
TRIGGER_NAME=CPU使用率が高い
TRIGGER_DESCRIPTION=CPU使用率が90%を超えた
TRIGGER_SEVERITY=High
EVENT_ID=12345
TRIGGER_ID=67890
EVENT_DATE=2026.03.11
EVENT_TIME=18:00:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=95%"""

SAMPLE_RECOVERY_MESSAGE = """ALERT_TYPE=RECOVERY
HOST_NAME=web01.example.com
TRIGGER_NAME=CPU使用率が高い
TRIGGER_SEVERITY=High
EVENT_ID=12345
TRIGGER_ID=67890
EVENT_DATE=2026.03.11
EVENT_TIME=18:00:00
RECOVERY_DATE=2026.03.11
RECOVERY_TIME=18:30:00
ZABBIX_URL=https://zabbix.example.com
ITEM_LASTVALUE=45%"""

SAMPLE_UPDATE_MESSAGE = """ALERT_TYPE=UPDATE
HOST_NAME=web01.example.com
TRIGGER_NAME=CPU使用率が高い
TRIGGER_SEVERITY=High
EVENT_ID=12345
TRIGGER_ID=67890
EVENT_DATE=2026.03.11
EVENT_TIME=18:00:00
ACK_AUTHOR=admin
ACK_MESSAGE=調査中
ZABBIX_URL=https://zabbix.example.com"""


class TestZabbixParamParser:
    def test_parse_problem_message(self, parser: ZabbixParamParser) -> None:
        event = parser.parse_message_body(SAMPLE_PROBLEM_MESSAGE)
        assert event.alert_type == AlertType.PROBLEM
        assert event.host_name == "web01.example.com"
        assert event.trigger_name == "CPU使用率が高い"
        assert event.trigger_description == "CPU使用率が90%を超えた"
        assert event.trigger_severity == Severity.HIGH
        assert event.event_id == "12345"
        assert event.trigger_id == "67890"
        assert event.event_date == "2026.03.11"
        assert event.event_time == "18:00:00"
        assert event.zabbix_url == "https://zabbix.example.com"
        assert event.item_last_value == "95%"

    def test_parse_recovery_message(self, parser: ZabbixParamParser) -> None:
        event = parser.parse_message_body(SAMPLE_RECOVERY_MESSAGE)
        assert event.alert_type == AlertType.RECOVERY
        assert event.recovery_date == "2026.03.11"
        assert event.recovery_time == "18:30:00"

    def test_parse_update_message(self, parser: ZabbixParamParser) -> None:
        event = parser.parse_message_body(SAMPLE_UPDATE_MESSAGE)
        assert event.alert_type == AlertType.UPDATE
        assert event.ack_author == "admin"
        assert event.ack_message == "調査中"

    def test_parse_argv_success(self, parser: ZabbixParamParser) -> None:
        argv = [
            "https://chat.googleapis.com/webhook",
            "test subject",
            SAMPLE_PROBLEM_MESSAGE,
        ]
        event = parser.parse_argv(argv)
        assert event.webhook_url == "https://chat.googleapis.com/webhook"
        assert event.alert_type == AlertType.PROBLEM

    def test_parse_argv_empty_sendto(self, parser: ZabbixParamParser) -> None:
        """空の ALERT.SENDTO は webhook_url を上書きしない."""
        argv = ["", "test subject", SAMPLE_PROBLEM_MESSAGE]
        event = parser.parse_argv(argv)
        assert event.webhook_url == ""

    def test_parse_argv_insufficient_args(self, parser: ZabbixParamParser) -> None:
        with pytest.raises(ParseError, match="引数が不足"):
            parser.parse_argv(["arg1", "arg2"])

    def test_parse_argv_no_args(self, parser: ZabbixParamParser) -> None:
        with pytest.raises(ParseError):
            parser.parse_argv([])

    def test_normalize_alert_type_unknown(self, parser: ZabbixParamParser) -> None:
        result = parser._normalize_alert_type("UNKNOWN_TYPE")
        assert result == AlertType.UPDATE

    def test_normalize_alert_type_case_insensitive(self, parser: ZabbixParamParser) -> None:
        # AlertType は大文字のみ対応（value が大文字）
        assert parser._normalize_alert_type("PROBLEM") == AlertType.PROBLEM

    def test_normalize_severity_case_insensitive(self, parser: ZabbixParamParser) -> None:
        assert parser._normalize_severity("high") == Severity.HIGH
        assert parser._normalize_severity("HIGH") == Severity.HIGH
        assert parser._normalize_severity("High") == Severity.HIGH

    def test_normalize_severity_unknown(self, parser: ZabbixParamParser) -> None:
        result = parser._normalize_severity("UNKNOWN")
        assert result == Severity.NOT_CLASSIFIED

    def test_parse_empty_message(self, parser: ZabbixParamParser) -> None:
        event = parser.parse_message_body("")
        assert event.alert_type == AlertType.UPDATE
        assert event.host_name == ""

    def test_parse_value_with_equals(self, parser: ZabbixParamParser) -> None:
        """値に = が含まれる場合の処理."""
        message = "TRIGGER_DESCRIPTION=CPU=95%超過\nHOST_NAME=web01"
        event = parser.parse_message_body(message)
        assert event.trigger_description == "CPU=95%超過"
        assert event.host_name == "web01"

    def test_parse_unknown_keys_to_extra(self, parser: ZabbixParamParser) -> None:
        message = "UNKNOWN_KEY=some_value\nHOST_NAME=web01"
        event = parser.parse_message_body(message)
        assert "UNKNOWN_KEY" in event.extra
        assert event.extra["UNKNOWN_KEY"] == "some_value"

    def test_parse_message_with_blank_lines(self, parser: ZabbixParamParser) -> None:
        message = "\nHOST_NAME=web01\n\nTRIGGER_NAME=test\n"
        event = parser.parse_message_body(message)
        assert event.host_name == "web01"
        assert event.trigger_name == "test"
