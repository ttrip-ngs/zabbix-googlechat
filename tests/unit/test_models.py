"""models.py のユニットテスト."""

from zabbix_googlechat.models import (
    ALERT_TYPE_EMOJI,
    ALERT_TYPE_LABEL,
    SEVERITY_EMOJI,
    AlertType,
    Severity,
    ZabbixEvent,
)


class TestAlertType:
    def test_values(self) -> None:
        assert AlertType.PROBLEM.value == "PROBLEM"
        assert AlertType.RECOVERY.value == "RECOVERY"
        assert AlertType.UPDATE.value == "UPDATE"

    def test_all_alert_types_have_emoji(self) -> None:
        for alert_type in AlertType:
            assert alert_type in ALERT_TYPE_EMOJI, f"{alert_type} に絵文字がない"

    def test_all_alert_types_have_label(self) -> None:
        for alert_type in AlertType:
            assert alert_type in ALERT_TYPE_LABEL, f"{alert_type} にラベルがない"


class TestSeverity:
    def test_values(self) -> None:
        assert Severity.NOT_CLASSIFIED.value == "Not classified"
        assert Severity.INFORMATION.value == "Information"
        assert Severity.WARNING.value == "Warning"
        assert Severity.AVERAGE.value == "Average"
        assert Severity.HIGH.value == "High"
        assert Severity.DISASTER.value == "Disaster"

    def test_all_severities_have_emoji(self) -> None:
        for severity in Severity:
            assert severity in SEVERITY_EMOJI, f"{severity} に絵文字がない"


class TestZabbixEvent:
    def test_default_values(self) -> None:
        event = ZabbixEvent()
        assert event.alert_type == AlertType.UPDATE
        assert event.host_name == ""
        assert event.trigger_name == ""
        assert event.trigger_severity == Severity.NOT_CLASSIFIED
        assert event.extra == {}

    def test_event_datetime_both(self) -> None:
        event = ZabbixEvent(event_date="2026.03.11", event_time="18:00:00")
        assert event.event_datetime == "2026.03.11 18:00:00"

    def test_event_datetime_date_only(self) -> None:
        event = ZabbixEvent(event_date="2026.03.11")
        assert event.event_datetime == "2026.03.11"

    def test_event_datetime_time_only(self) -> None:
        event = ZabbixEvent(event_time="18:00:00")
        assert event.event_datetime == "18:00:00"

    def test_event_datetime_empty(self) -> None:
        event = ZabbixEvent()
        assert event.event_datetime == ""

    def test_recovery_datetime_both(self) -> None:
        event = ZabbixEvent(recovery_date="2026.03.11", recovery_time="19:00:00")
        assert event.recovery_datetime == "2026.03.11 19:00:00"

    def test_recovery_datetime_empty(self) -> None:
        event = ZabbixEvent()
        assert event.recovery_datetime == ""

    def test_custom_values(self) -> None:
        event = ZabbixEvent(
            alert_type=AlertType.PROBLEM,
            host_name="web01.example.com",
            trigger_name="CPU使用率が高い",
            trigger_severity=Severity.HIGH,
            event_id="12345",
        )
        assert event.alert_type == AlertType.PROBLEM
        assert event.host_name == "web01.example.com"
        assert event.trigger_name == "CPU使用率が高い"
        assert event.trigger_severity == Severity.HIGH
        assert event.event_id == "12345"
