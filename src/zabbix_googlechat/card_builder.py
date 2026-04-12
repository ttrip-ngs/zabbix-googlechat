"""Google Chat Card v2 ビルダー."""

from __future__ import annotations

import logging
from typing import Any

from zabbix_googlechat.models import (
    ALERT_TYPE_EMOJI,
    ALERT_TYPE_LABEL,
    SEVERITY_EMOJI,
    AlertType,
    ZabbixEvent,
)

logger = logging.getLogger(__name__)


class GoogleChatCardBuilder:
    """Google Chat Card v2 形式のペイロードビルダー.

    カード構造:
        ┌─────────────────────────────┐
        │ 🔴 [PROBLEM] web01.example  │  ← ヘッダー
        │    CPU使用率が高い           │
        ├─────────────────────────────┤
        │ 🖥️ ホスト: web01.example    │  ← 問題詳細セクション
        │ ⚠️ 重要度: High             │
        │ 📊 現在値: 95%              │
        ├─────────────────────────────┤
        │ 🕐 発生: 2026-03-11 18:00   │  ← イベント詳細セクション
        │ 🆔 イベントID: 12345        │
        ├─────────────────────────────┤
        │ [Zabbixで確認する →]        │  ← アクションセクション
        └─────────────────────────────┘
    """

    def __init__(self, event: ZabbixEvent) -> None:
        self._event = event

    def build(self) -> dict[str, Any]:
        """Google Chat cardsV2 形式のペイロードを構築する.

        Returns:
            cardsV2 ペイロード辞書
        """
        sections: list[dict[str, Any]] = []

        # 問題詳細セクション
        problem_section = self._build_problem_section()
        if problem_section:
            sections.append(problem_section)

        # イベント詳細セクション
        detail_section = self._build_detail_section()
        if detail_section:
            sections.append(detail_section)

        # アクションセクション（Zabbixリンク）
        action_section = self._build_action_section()
        if action_section:
            sections.append(action_section)

        card: dict[str, Any] = {
            "cardsV2": [
                {
                    "cardId": f"zabbix-alert-{self._event.event_id or 'unknown'}",
                    "card": {
                        "header": self._build_header(),
                        "sections": sections,
                    },
                }
            ]
        }

        return card

    def _build_header(self) -> dict[str, Any]:
        """カードヘッダーを構築する."""
        alert_type = self._event.alert_type
        type_emoji = ALERT_TYPE_EMOJI.get(alert_type, "🔵")
        type_label = ALERT_TYPE_LABEL.get(alert_type, "UPDATE")

        # タイトル: 絵文字 + アラートタイプ + ホスト名
        title = f"{type_emoji} [{type_label}] {self._event.host_name or '(ホスト不明)'}"

        # サブタイトル: トリガー名
        subtitle = self._event.trigger_name or "(トリガー不明)"

        return {
            "title": title,
            "subtitle": subtitle,
        }

    def _build_problem_section(self) -> dict[str, Any] | None:
        """問題詳細セクションを構築する."""
        widgets: list[dict[str, Any]] = []

        # ホスト名
        if self._event.host_name:
            widgets.append(
                self._make_decorated_text(
                    top_label="ホスト",
                    text=self._event.host_name,
                    start_icon="🖥️",
                )
            )

        # 重要度
        severity = self._event.trigger_severity
        severity_emoji = SEVERITY_EMOJI.get(severity, "⚪")
        widgets.append(
            self._make_decorated_text(
                top_label="重要度",
                text=f"{severity_emoji} {severity.value}",
                start_icon="⚠️",
            )
        )

        # トリガー詳細（説明があれば）
        if self._event.trigger_description:
            widgets.append(
                self._make_decorated_text(
                    top_label="詳細",
                    text=self._event.trigger_description,
                    start_icon="📝",
                )
            )

        # 現在値
        if self._event.item_last_value:
            widgets.append(
                self._make_decorated_text(
                    top_label="現在値",
                    text=self._event.item_last_value,
                    start_icon="📊",
                )
            )

        if not widgets:
            return None

        return {
            "header": "問題情報",
            "widgets": widgets,
        }

    def _build_detail_section(self) -> dict[str, Any] | None:
        """イベント詳細セクションを構築する."""
        widgets: list[dict[str, Any]] = []

        # 発生日時
        if self._event.event_datetime:
            widgets.append(
                self._make_decorated_text(
                    top_label="発生日時",
                    text=self._event.event_datetime,
                    start_icon="🕐",
                )
            )

        # イベントID
        if self._event.event_id:
            widgets.append(
                self._make_decorated_text(
                    top_label="イベントID",
                    text=self._event.event_id,
                    start_icon="🆔",
                )
            )

        # 復旧日時（RECOVERY時）
        if self._event.alert_type == AlertType.RECOVERY and self._event.recovery_datetime:
            widgets.append(
                self._make_decorated_text(
                    top_label="復旧日時",
                    text=self._event.recovery_datetime,
                    start_icon="🟢",
                )
            )

        # 確認メッセージ（UPDATE時）
        if self._event.alert_type == AlertType.UPDATE:
            if self._event.ack_author:
                widgets.append(
                    self._make_decorated_text(
                        top_label="確認者",
                        text=self._event.ack_author,
                        start_icon="👤",
                    )
                )
            if self._event.ack_message:
                widgets.append(
                    self._make_decorated_text(
                        top_label="確認メッセージ",
                        text=self._event.ack_message,
                        start_icon="💬",
                    )
                )

        if not widgets:
            return None

        return {
            "header": "イベント情報",
            "widgets": widgets,
        }

    def _build_action_section(self) -> dict[str, Any] | None:
        """アクションセクション（Zabbixリンクボタン）を構築する."""
        if not self._event.zabbix_url:
            return None

        # イベントIDがある場合はイベント詳細ページへのリンクを生成
        if self._event.event_id:
            # Zabbix 6.x以降のイベント詳細URL形式
            link_url = (
                f"{self._event.zabbix_url.rstrip('/')}"
                f"/tr_events.php?triggerid={self._event.trigger_id}&eventid={self._event.event_id}"
            )
        else:
            link_url = self._event.zabbix_url

        return {
            "widgets": [
                {
                    "buttonList": {
                        "buttons": [
                            {
                                "text": "Zabbixで確認する →",
                                "onClick": {
                                    "openLink": {
                                        "url": link_url,
                                    }
                                },
                            }
                        ]
                    }
                }
            ]
        }

    @staticmethod
    def _make_decorated_text(
        top_label: str,
        text: str,
        start_icon: str = "",
    ) -> dict[str, Any]:
        """decoratedText ウィジェットを作成する."""
        widget: dict[str, Any] = {
            "decoratedText": {
                "topLabel": top_label,
                "text": text,
            }
        }
        if start_icon:
            widget["decoratedText"]["startIcon"] = {
                "altText": start_icon,
                "knownIcon": "DESCRIPTION",
                "iconUrl": "",
                # Google Chat では絵文字テキストをアイコン代わりに使用
                # 実際の表示はtextに絵文字を含めることで対応
            }
            # シンプルに絵文字をテキストに含める形式を採用
            widget["decoratedText"]["text"] = f"{start_icon} {text}"
            del widget["decoratedText"]["startIcon"]

        return widget
