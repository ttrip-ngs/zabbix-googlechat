"""card_builder.py のユニットテスト."""

import pytest

from zabbix_googlechat.card_builder import GoogleChatCardBuilder
from zabbix_googlechat.models import AlertType, Severity, ZabbixEvent


@pytest.fixture
def problem_event() -> ZabbixEvent:
    return ZabbixEvent(
        alert_type=AlertType.PROBLEM,
        host_name="web01.example.com",
        trigger_name="CPU使用率が高い",
        trigger_description="CPU使用率が90%を超えた",
        trigger_severity=Severity.HIGH,
        event_id="12345",
        trigger_id="67890",
        event_date="2026.03.11",
        event_time="18:00:00",
        zabbix_url="https://zabbix.example.com",
        item_last_value="95%",
    )


@pytest.fixture
def recovery_event() -> ZabbixEvent:
    return ZabbixEvent(
        alert_type=AlertType.RECOVERY,
        host_name="web01.example.com",
        trigger_name="CPU使用率が高い",
        trigger_severity=Severity.HIGH,
        event_id="12345",
        trigger_id="67890",
        event_date="2026.03.11",
        event_time="18:00:00",
        recovery_date="2026.03.11",
        recovery_time="18:30:00",
        zabbix_url="https://zabbix.example.com",
    )


@pytest.fixture
def update_event() -> ZabbixEvent:
    return ZabbixEvent(
        alert_type=AlertType.UPDATE,
        host_name="web01.example.com",
        trigger_name="CPU使用率が高い",
        trigger_severity=Severity.HIGH,
        event_id="12345",
        trigger_id="67890",
        event_date="2026.03.11",
        event_time="18:00:00",
        ack_author="admin",
        ack_message="調査中",
        zabbix_url="https://zabbix.example.com",
    )


class TestGoogleChatCardBuilder:
    def test_build_returns_cards_v2(self, problem_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(problem_event)
        payload = builder.build()
        assert "cardsV2" in payload
        assert isinstance(payload["cardsV2"], list)
        assert len(payload["cardsV2"]) == 1

    def test_build_card_id(self, problem_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(problem_event)
        payload = builder.build()
        card_id = payload["cardsV2"][0]["cardId"]
        assert "12345" in card_id

    def test_header_problem(self, problem_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(problem_event)
        payload = builder.build()
        header = payload["cardsV2"][0]["card"]["header"]
        assert "PROBLEM" in header["title"]
        assert "🔴" in header["title"]
        assert "web01.example.com" in header["title"]
        assert "CPU使用率が高い" in header["subtitle"]

    def test_header_recovery(self, recovery_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(recovery_event)
        payload = builder.build()
        header = payload["cardsV2"][0]["card"]["header"]
        assert "RECOVERY" in header["title"]
        assert "🟢" in header["title"]

    def test_header_update(self, update_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(update_event)
        payload = builder.build()
        header = payload["cardsV2"][0]["card"]["header"]
        assert "UPDATE" in header["title"]
        assert "🔵" in header["title"]

    def test_problem_section_exists(self, problem_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(problem_event)
        payload = builder.build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        section_headers = [s.get("header", "") for s in sections]
        assert "問題情報" in section_headers

    def test_problem_section_contains_severity(self, problem_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(problem_event)
        payload = builder.build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        problem_section = next(s for s in sections if s.get("header") == "問題情報")
        widgets_text = str(problem_section["widgets"])
        assert "High" in widgets_text

    def test_detail_section_exists(self, problem_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(problem_event)
        payload = builder.build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        section_headers = [s.get("header", "") for s in sections]
        assert "イベント情報" in section_headers

    def test_recovery_section_has_recovery_time(self, recovery_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(recovery_event)
        payload = builder.build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        detail_section = next(s for s in sections if s.get("header") == "イベント情報")
        widgets_text = str(detail_section["widgets"])
        assert "18:30:00" in widgets_text

    def test_update_section_has_ack_message(self, update_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(update_event)
        payload = builder.build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        detail_section = next(s for s in sections if s.get("header") == "イベント情報")
        widgets_text = str(detail_section["widgets"])
        assert "調査中" in widgets_text

    def test_action_section_with_url(self, problem_event: ZabbixEvent) -> None:
        builder = GoogleChatCardBuilder(problem_event)
        payload = builder.build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        # アクションセクションはheaderなし
        action_sections = [s for s in sections if "header" not in s]
        assert len(action_sections) > 0
        buttons = action_sections[0]["widgets"][0]["buttonList"]["buttons"]
        assert len(buttons) > 0
        assert "Zabbixで確認する" in buttons[0]["text"]
        button_url = buttons[0]["onClick"]["openLink"]["url"]
        assert "triggerid=67890" in button_url
        assert "eventid=12345" in button_url

    def test_action_section_without_url(self) -> None:
        event = ZabbixEvent(
            alert_type=AlertType.PROBLEM,
            host_name="web01",
            trigger_name="test",
            # zabbix_url は空
        )
        builder = GoogleChatCardBuilder(event)
        payload = builder.build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        # アクションセクションは含まれない
        action_sections = [
            s
            for s in sections
            if "widgets" in s and any("buttonList" in str(w) for w in s["widgets"])
        ]
        assert len(action_sections) == 0

    def test_build_minimal_event(self) -> None:
        """最小限の情報でもビルドが成功すること."""
        event = ZabbixEvent()
        builder = GoogleChatCardBuilder(event)
        payload = builder.build()
        assert "cardsV2" in payload
