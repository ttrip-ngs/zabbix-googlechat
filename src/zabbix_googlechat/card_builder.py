"""Google Chat メッセージペイロードビルダー.

メッセージスタイルは 4 種類:
    detailed: 2セクション + 各項目 decoratedText(topLabel+text)（情報量重視・既定）
    medium:   2セクション維持・各項目を topLabel 無しの1行 decoratedText に圧縮
    compact:  ヘッダー + textParagraph 1枚 + ボタン（カード1枚に集約）
    text:     cardsV2 を使わないプレーンテキスト（最小スペース）

外部からは build_payload(event, style) を呼び出してペイロード辞書を取得する。
GoogleChatCardBuilder は detailed スタイルの実装であり、後方互換のため公開している。
"""

from __future__ import annotations

import logging
from typing import Any

from zabbix_googlechat.models import (
    ALERT_TYPE_EMOJI,
    ALERT_TYPE_LABEL,
    DEFAULT_CARD_STYLE,
    SEVERITY_EMOJI,
    AlertType,
    CardStyle,
    ZabbixEvent,
)

logger = logging.getLogger(__name__)


class _CardBuilderBase:
    """各スタイルのビルダーが共有する基底クラス.

    ヘッダー構築・Zabbixリンク生成・アクションボタン・絵文字解決など、
    スタイル間で共通の処理を提供する。
    """

    def __init__(self, event: ZabbixEvent) -> None:
        self._event = event

    def build(self) -> dict[str, Any]:
        """Google Chat 送信ペイロードを構築する（サブクラスで実装）."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # 共通ヘルパー
    # ------------------------------------------------------------------
    def _alert_emoji(self) -> str:
        """アラートタイプ別の絵文字を返す."""
        return ALERT_TYPE_EMOJI.get(self._event.alert_type, "🔵")

    def _alert_label(self) -> str:
        """アラートタイプ別の表示名を返す."""
        return ALERT_TYPE_LABEL.get(self._event.alert_type, "UPDATE")

    def _severity_text(self) -> str:
        """重要度の絵文字付き表示文字列を返す."""
        severity = self._event.trigger_severity
        emoji = SEVERITY_EMOJI.get(severity, "⚪")
        return f"{emoji} {severity.value}"

    def _title(self) -> str:
        """タイトル文字列（絵文字 + アラートタイプ + ホスト名）を返す."""
        return (
            f"{self._alert_emoji()} [{self._alert_label()}] "
            f"{self._event.host_name or '(ホスト不明)'}"
        )

    def _subtitle(self) -> str:
        """サブタイトル文字列（トリガー名）を返す."""
        return self._event.trigger_name or "(トリガー不明)"

    def _build_header(self) -> dict[str, Any]:
        """カードヘッダーを構築する."""
        return {
            "title": self._title(),
            "subtitle": self._subtitle(),
        }

    def _link_url(self) -> str | None:
        """Zabbixイベント詳細ページへのリンクURLを生成する.

        Returns:
            リンクURL。zabbix_url が未設定の場合は None。
        """
        if not self._event.zabbix_url:
            return None

        # イベントIDがある場合は Zabbix 6.x 以降のイベント詳細URL形式を使う
        if self._event.event_id:
            return (
                f"{self._event.zabbix_url.rstrip('/')}"
                f"/tr_events.php?triggerid={self._event.trigger_id}"
                f"&eventid={self._event.event_id}"
            )
        return self._event.zabbix_url

    def _build_action_section(self) -> dict[str, Any] | None:
        """アクションセクション（Zabbixリンクボタン）を構築する."""
        link_url = self._link_url()
        if not link_url:
            return None

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

    def _wrap_card(self, sections: list[dict[str, Any]]) -> dict[str, Any]:
        """セクションリストを cardsV2 ペイロードにラップする."""
        return {
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


class GoogleChatCardBuilder(_CardBuilderBase):
    """detailed スタイル: Google Chat Card v2 形式のペイロードビルダー.

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

        return self._wrap_card(sections)

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
        widgets.append(
            self._make_decorated_text(
                top_label="重要度",
                text=self._severity_text(),
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

    @staticmethod
    def _make_decorated_text(
        top_label: str,
        text: str,
        start_icon: str = "",
    ) -> dict[str, Any]:
        """decoratedText ウィジェットを作成する.

        Google Chat の startIcon は絵文字に非対応のため、絵文字は text 先頭に含める。
        """
        display_text = f"{start_icon} {text}" if start_icon else text
        return {
            "decoratedText": {
                "topLabel": top_label,
                "text": display_text,
            }
        }


class MediumCardBuilder(_CardBuilderBase):
    """medium スタイル: 2セクション構造を維持しつつ各項目を1行に圧縮する.

    detailed との違いは decoratedText に topLabel を付けず、`絵文字 ラベル: 値` を
    text のみで表現する点。これにより1項目あたりの縦幅が約半分になる。
    """

    def build(self) -> dict[str, Any]:
        """cardsV2 ペイロードを構築する."""
        sections: list[dict[str, Any]] = []

        problem_section = self._build_problem_section()
        if problem_section:
            sections.append(problem_section)

        detail_section = self._build_detail_section()
        if detail_section:
            sections.append(detail_section)

        action_section = self._build_action_section()
        if action_section:
            sections.append(action_section)

        return self._wrap_card(sections)

    def _build_problem_section(self) -> dict[str, Any] | None:
        """問題詳細セクションを構築する（1行表示）."""
        widgets: list[dict[str, Any]] = []

        if self._event.host_name:
            widgets.append(self._make_inline_text("🖥️", "ホスト", self._event.host_name))

        widgets.append(self._make_inline_text("⚠️", "重要度", self._severity_text()))

        if self._event.trigger_description:
            widgets.append(self._make_inline_text("📝", "詳細", self._event.trigger_description))

        if self._event.item_last_value:
            widgets.append(self._make_inline_text("📊", "現在値", self._event.item_last_value))

        if not widgets:
            return None

        return {"header": "問題情報", "widgets": widgets}

    def _build_detail_section(self) -> dict[str, Any] | None:
        """イベント詳細セクションを構築する（1行表示）."""
        widgets: list[dict[str, Any]] = []

        if self._event.event_datetime:
            widgets.append(self._make_inline_text("🕐", "発生日時", self._event.event_datetime))

        if self._event.event_id:
            widgets.append(self._make_inline_text("🆔", "イベントID", self._event.event_id))

        if self._event.alert_type == AlertType.RECOVERY and self._event.recovery_datetime:
            widgets.append(self._make_inline_text("🟢", "復旧日時", self._event.recovery_datetime))

        if self._event.alert_type == AlertType.UPDATE:
            if self._event.ack_author:
                widgets.append(self._make_inline_text("👤", "確認者", self._event.ack_author))
            if self._event.ack_message:
                widgets.append(
                    self._make_inline_text("💬", "確認メッセージ", self._event.ack_message)
                )

        if not widgets:
            return None

        return {"header": "イベント情報", "widgets": widgets}

    @staticmethod
    def _make_inline_text(emoji: str, label: str, value: str) -> dict[str, Any]:
        """topLabel を使わず `絵文字 ラベル: 値` を1行で表す decoratedText を作成する."""
        return {"decoratedText": {"text": f"{emoji} <b>{label}:</b> {value}"}}


class CompactCardBuilder(_CardBuilderBase):
    """compact スタイル: ヘッダー + textParagraph 1枚 + ボタンに集約する.

    textParagraph は改行に <br>、装飾に <b> を用いる（Google Chat の制限に準拠）。
    """

    def build(self) -> dict[str, Any]:
        """cardsV2 ペイロードを構築する."""
        sections: list[dict[str, Any]] = []

        body = self._build_body_lines()
        if body:
            sections.append(
                {
                    "widgets": [{"textParagraph": {"text": "<br>".join(body)}}],
                }
            )

        action_section = self._build_action_section()
        if action_section:
            sections.append(action_section)

        return self._wrap_card(sections)

    def _build_body_lines(self) -> list[str]:
        """textParagraph に表示する行リストを構築する."""
        lines: list[str] = []

        # 重要度（重要度名を太字、現在値があれば同じ行に併記）
        severity = self._event.trigger_severity
        severity_emoji = SEVERITY_EMOJI.get(severity, "⚪")
        severity_line = f"{severity_emoji} <b>{severity.value}</b>"
        if self._event.item_last_value:
            severity_line += f" ・ 📊 {self._event.item_last_value}"
        lines.append(severity_line)

        # トリガー詳細
        if self._event.trigger_description:
            lines.append(f"📝 {self._event.trigger_description}")

        # 発生日時（RECOVERY時は復旧日時を矢印で併記）
        if self._event.event_datetime:
            time_line = f"🕐 {self._event.event_datetime}"
            if self._event.alert_type == AlertType.RECOVERY and self._event.recovery_datetime:
                time_line += f" → 🟢 {self._event.recovery_datetime}"
            lines.append(time_line)

        # 確認情報（UPDATE時）
        if self._event.alert_type == AlertType.UPDATE:
            ack_parts: list[str] = []
            if self._event.ack_author:
                ack_parts.append(f"👤 {self._event.ack_author}")
            if self._event.ack_message:
                ack_parts.append(f"💬 {self._event.ack_message}")
            if ack_parts:
                lines.append(" ・ ".join(ack_parts))

        # イベントID
        if self._event.event_id:
            lines.append(f"🆔 {self._event.event_id}")

        return lines


class PlainTextBuilder(_CardBuilderBase):
    """text スタイル: cardsV2 を使わないプレーンテキストメッセージを構築する.

    プレーンテキストは改行(\\n)と *bold* 記法に対応する。Zabbixリンクは末尾にURLを記載。
    """

    def build(self) -> dict[str, Any]:
        """プレーンテキストペイロード({"text": ...})を構築する."""
        lines: list[str] = [self._title()]

        # トリガー名（太字）
        lines.append(f"*{self._subtitle()}*")

        # 重要度（+ 現在値）
        severity_line = self._severity_text()
        if self._event.item_last_value:
            severity_line += f" ・ 📊 {self._event.item_last_value}"
        lines.append(severity_line)

        # トリガー詳細
        if self._event.trigger_description:
            lines.append(f"📝 {self._event.trigger_description}")

        # 発生日時
        if self._event.event_datetime:
            lines.append(f"🕐 発生 {self._event.event_datetime}")

        # 復旧日時（RECOVERY時）
        if self._event.alert_type == AlertType.RECOVERY and self._event.recovery_datetime:
            lines.append(f"🟢 復旧 {self._event.recovery_datetime}")

        # 確認情報（UPDATE時）
        if self._event.alert_type == AlertType.UPDATE:
            if self._event.ack_author:
                lines.append(f"👤 確認者 {self._event.ack_author}")
            if self._event.ack_message:
                lines.append(f"💬 {self._event.ack_message}")

        # イベントID
        if self._event.event_id:
            lines.append(f"🆔 {self._event.event_id}")

        # Zabbixリンク
        link_url = self._link_url()
        if link_url:
            lines.append(f"🔗 {link_url}")

        return {"text": "\n".join(lines)}


# スタイル値 → ビルダークラスのマッピング
_BUILDERS: dict[str, type[_CardBuilderBase]] = {
    CardStyle.DETAILED.value: GoogleChatCardBuilder,
    CardStyle.MEDIUM.value: MediumCardBuilder,
    CardStyle.COMPACT.value: CompactCardBuilder,
    CardStyle.TEXT.value: PlainTextBuilder,
}


def build_payload(event: ZabbixEvent, style: str) -> dict[str, Any]:
    """指定スタイルで Google Chat 送信ペイロードを構築する.

    未知のスタイルが渡された場合は警告のうえ既定スタイル(detailed)へフォールバックする
    （スタイル指定ミスで通知自体が失われるのを防ぐ）。

    Args:
        event: Zabbixイベントデータ
        style: メッセージスタイル（detailed / medium / compact / text）

    Returns:
        Google Chat Webhook へ送信するペイロード辞書
    """
    builder_cls = _BUILDERS.get(style)
    if builder_cls is None:
        logger.warning(
            "未知のメッセージスタイル '%s'、'%s' にフォールバックします", style, DEFAULT_CARD_STYLE
        )
        builder_cls = _BUILDERS[DEFAULT_CARD_STYLE]

    return builder_cls(event).build()
