"""card_builder.py のユニットテスト."""

import pytest

from zabbix_googlechat.card_builder import (
    CompactCardBuilder,
    GoogleChatCardBuilder,
    MediumCardBuilder,
    PlainTextBuilder,
    build_payload,
)
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


class TestMediumCardBuilder:
    def test_build_returns_cards_v2(self, problem_event: ZabbixEvent) -> None:
        payload = MediumCardBuilder(problem_event).build()
        assert "cardsV2" in payload

    def test_sections_preserved(self, problem_event: ZabbixEvent) -> None:
        """detailed と同じ2セクション構造を維持する."""
        payload = MediumCardBuilder(problem_event).build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        headers = [s.get("header", "") for s in sections]
        assert "問題情報" in headers
        assert "イベント情報" in headers

    def test_no_top_label(self, problem_event: ZabbixEvent) -> None:
        """各 decoratedText に topLabel を付けない（縦幅圧縮）."""
        payload = MediumCardBuilder(problem_event).build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        for section in sections:
            for widget in section["widgets"]:
                deco = widget.get("decoratedText")
                if deco is not None:
                    assert "topLabel" not in deco

    def test_contains_values(self, problem_event: ZabbixEvent) -> None:
        payload = MediumCardBuilder(problem_event).build()
        text = str(payload)
        assert "web01.example.com" in text
        assert "High" in text


class TestCompactCardBuilder:
    def test_build_returns_cards_v2(self, problem_event: ZabbixEvent) -> None:
        payload = CompactCardBuilder(problem_event).build()
        assert "cardsV2" in payload

    def test_uses_text_paragraph(self, problem_event: ZabbixEvent) -> None:
        """本文は単一の textParagraph ウィジェットに集約される."""
        payload = CompactCardBuilder(problem_event).build()
        sections = payload["cardsV2"][0]["card"]["sections"]
        body_section = sections[0]
        assert "textParagraph" in body_section["widgets"][0]
        # 改行は <br>（Google Chat の textParagraph 仕様）
        assert "<br>" in body_section["widgets"][0]["textParagraph"]["text"]

    def test_has_action_button(self, problem_event: ZabbixEvent) -> None:
        payload = CompactCardBuilder(problem_event).build()
        text = str(payload)
        assert "Zabbixで確認する" in text

    def test_recovery_shows_recovery_time(self, recovery_event: ZabbixEvent) -> None:
        payload = CompactCardBuilder(recovery_event).build()
        assert "18:30:00" in str(payload)


class TestPlainTextBuilder:
    def test_no_cards_v2(self, problem_event: ZabbixEvent) -> None:
        """text スタイルは cardsV2 を持たない."""
        payload = PlainTextBuilder(problem_event).build()
        assert "cardsV2" not in payload
        assert "text" in payload

    def test_contains_key_info(self, problem_event: ZabbixEvent) -> None:
        payload = PlainTextBuilder(problem_event).build()
        text = payload["text"]
        assert "PROBLEM" in text
        assert "web01.example.com" in text
        assert "High" in text
        assert "https://zabbix.example.com" in text

    def test_recovery_shows_recovery_time(self, recovery_event: ZabbixEvent) -> None:
        payload = PlainTextBuilder(recovery_event).build()
        assert "18:30:00" in payload["text"]


class TestBuildPayloadFactory:
    def test_detailed(self, problem_event: ZabbixEvent) -> None:
        payload = build_payload(problem_event, "detailed")
        sections = payload["cardsV2"][0]["card"]["sections"]
        # detailed は topLabel 付き decoratedText を使う
        assert any("topLabel" in w.get("decoratedText", {}) for s in sections for w in s["widgets"])

    def test_medium(self, problem_event: ZabbixEvent) -> None:
        payload = build_payload(problem_event, "medium")
        assert "cardsV2" in payload

    def test_compact(self, problem_event: ZabbixEvent) -> None:
        payload = build_payload(problem_event, "compact")
        sections = payload["cardsV2"][0]["card"]["sections"]
        assert "textParagraph" in sections[0]["widgets"][0]

    def test_text(self, problem_event: ZabbixEvent) -> None:
        payload = build_payload(problem_event, "text")
        assert "cardsV2" not in payload
        assert "text" in payload

    def test_unknown_style_falls_back_to_detailed(self, problem_event: ZabbixEvent) -> None:
        """未知スタイルは detailed にフォールバックする（通知は失わない）."""
        payload = build_payload(problem_event, "bogus")
        detailed = build_payload(problem_event, "detailed")
        assert payload == detailed
