"""カスタム例外クラス定義."""

from __future__ import annotations


class ZabbixGoogleChatError(Exception):
    """ライブラリ基底例外クラス."""


class ConfigurationError(ZabbixGoogleChatError):
    """設定エラー（必須設定が未定義、不正な値等）."""


class ParseError(ZabbixGoogleChatError):
    """Zabbixパラメータのパースエラー."""


class WebhookConnectionError(ZabbixGoogleChatError):
    """Webhook接続エラー（ネットワーク障害、リトライ上限超過等）."""

    def __init__(self, message: str, retry_count: int = 0) -> None:
        super().__init__(message)
        self.retry_count = retry_count


class WebhookPayloadError(ZabbixGoogleChatError):
    """Webhookペイロードエラー（400 Bad Request等）."""

    def __init__(self, message: str, status_code: int = 0, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
