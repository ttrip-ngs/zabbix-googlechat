"""Zabbix アラート通知のデータモデルと定数定義."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AlertType(str, Enum):
    """アラートタイプ."""

    PROBLEM = "PROBLEM"
    RECOVERY = "RECOVERY"
    UPDATE = "UPDATE"


class CardStyle(str, Enum):
    """Google Chat メッセージスタイル.

    detailed: 2セクション + 各項目 decoratedText(topLabel+text)（情報量重視・既定）
    medium:   2セクション維持・各項目を topLabel 無し1行に圧縮
    compact:  ヘッダー + textParagraph 1枚 + ボタン（カード1枚に集約）
    text:     cardsV2 を使わないプレーンテキスト（最小スペース）
    """

    DETAILED = "detailed"
    MEDIUM = "medium"
    COMPACT = "compact"
    TEXT = "text"


# デフォルトのメッセージスタイル
DEFAULT_CARD_STYLE = CardStyle.DETAILED.value


class Severity(str, Enum):
    """Zabbix トリガー重要度."""

    NOT_CLASSIFIED = "Not classified"
    INFORMATION = "Information"
    WARNING = "Warning"
    AVERAGE = "Average"
    HIGH = "High"
    DISASTER = "Disaster"


# 重要度別絵文字マッピング
SEVERITY_EMOJI: dict[Severity, str] = {
    Severity.NOT_CLASSIFIED: "⚪",
    Severity.INFORMATION: "🔵",
    Severity.WARNING: "🟡",
    Severity.AVERAGE: "🟠",
    Severity.HIGH: "🔴",
    Severity.DISASTER: "🔥",
}

# アラートタイプ別絵文字マッピング
ALERT_TYPE_EMOJI: dict[AlertType, str] = {
    AlertType.PROBLEM: "🔴",
    AlertType.RECOVERY: "🟢",
    AlertType.UPDATE: "🔵",
}

# アラートタイプ別表示名
ALERT_TYPE_LABEL: dict[AlertType, str] = {
    AlertType.PROBLEM: "PROBLEM",
    AlertType.RECOVERY: "RECOVERY",
    AlertType.UPDATE: "UPDATE",
}


@dataclass
class ZabbixEvent:
    """Zabbix アラートイベントデータ."""

    # アラート基本情報
    alert_type: AlertType = AlertType.UPDATE
    host_name: str = ""
    trigger_name: str = ""
    trigger_description: str = ""
    trigger_severity: Severity = Severity.NOT_CLASSIFIED

    # イベント情報
    event_id: str = ""
    trigger_id: str = ""
    event_date: str = ""
    event_time: str = ""

    # 復旧情報（RECOVERY時）
    recovery_date: str = ""
    recovery_time: str = ""

    # 確認情報（UPDATE時）
    ack_message: str = ""
    ack_author: str = ""

    # 現在値
    item_last_value: str = ""

    # Zabbix URL（ダッシュボードリンク用）
    zabbix_url: str = ""

    # Webhook送信先（{ALERT.SENDTO}から取得）
    webhook_url: str = ""

    # メッセージスタイル（アクション単位の上書き値。空=未指定で設定ファイルの値を使用）
    card_style: str = ""

    # アラートメッセージ全文（デバッグ用）
    raw_message: str = ""

    # 追加パラメータ（未知キーの格納用）
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def event_datetime(self) -> str:
        """発生日時の整形文字列."""
        if self.event_date and self.event_time:
            return f"{self.event_date} {self.event_time}"
        return self.event_date or self.event_time or ""

    @property
    def recovery_datetime(self) -> str:
        """復旧日時の整形文字列."""
        if self.recovery_date and self.recovery_time:
            return f"{self.recovery_date} {self.recovery_time}"
        return self.recovery_date or self.recovery_time or ""
