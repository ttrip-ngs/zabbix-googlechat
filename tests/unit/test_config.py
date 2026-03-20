"""config.py のユニットテスト."""

from pathlib import Path

import pytest
import yaml

from zabbix_googlechat.config import NotificationConfig
from zabbix_googlechat.exceptions import ConfigurationError


@pytest.fixture
def sample_yaml(tmp_path: Path) -> Path:
    data = {
        "googlechat": {
            "webhook_url": "https://chat.googleapis.com/v1/spaces/test",
            "timeout": 15,
            "max_retries": 5,
            "retry_delay": 2.0,
        },
        "zabbix": {"url": "https://zabbix.example.com"},
        "logging": {"level": "DEBUG"},
    }
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml.dump(data), encoding="utf-8")
    return yaml_file


class TestNotificationConfig:
    def test_default_values(self) -> None:
        config = NotificationConfig()
        assert config.webhook_url == ""
        assert config.timeout == 10
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.log_level == "INFO"

    def test_from_yaml(self, sample_yaml: Path) -> None:
        config = NotificationConfig.from_yaml(sample_yaml)
        assert config.webhook_url == "https://chat.googleapis.com/v1/spaces/test"
        assert config.timeout == 15
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
        assert config.zabbix_url == "https://zabbix.example.com"
        assert config.log_level == "DEBUG"

    def test_from_yaml_not_found(self) -> None:
        with pytest.raises(ConfigurationError, match="設定ファイルが見つかりません"):
            NotificationConfig.from_yaml("/nonexistent/path/config.yaml")

    def test_from_yaml_invalid_yaml(self, tmp_path: Path) -> None:
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("invalid: [yaml: content", encoding="utf-8")
        with pytest.raises(ConfigurationError, match="YAMLパースエラー"):
            NotificationConfig.from_yaml(invalid_yaml)

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("GCHAT_WEBHOOK_URL", "https://chat.googleapis.com/env-webhook")
        monkeypatch.setenv("ZABBIX_URL", "https://zabbix-env.example.com")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("GCHAT_TIMEOUT", "20")
        monkeypatch.setenv("GCHAT_MAX_RETRIES", "5")

        config = NotificationConfig.from_env()
        assert config.webhook_url == "https://chat.googleapis.com/env-webhook"
        assert config.zabbix_url == "https://zabbix-env.example.com"
        assert config.log_level == "DEBUG"
        assert config.timeout == 20
        assert config.max_retries == 5

    def test_load_priority_env_over_yaml(
        self, sample_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数はYAMLより優先される."""
        monkeypatch.setenv("GCHAT_WEBHOOK_URL", "https://chat.googleapis.com/env-webhook")
        config = NotificationConfig.load(yaml_path=sample_yaml)
        assert config.webhook_url == "https://chat.googleapis.com/env-webhook"

    def test_load_priority_yaml_over_sendto(self, sample_yaml: Path) -> None:
        """YAMLはALERT.SENDTOより優先される."""
        config = NotificationConfig.load(
            yaml_path=sample_yaml,
            alert_sendto="https://chat.googleapis.com/sendto-webhook",
        )
        assert config.webhook_url == "https://chat.googleapis.com/v1/spaces/test"

    def test_load_sendto_as_fallback(self) -> None:
        """YAMLも環境変数もない場合はALERT.SENDTOを使用."""
        config = NotificationConfig.load(
            alert_sendto="https://chat.googleapis.com/sendto-webhook",
        )
        assert config.webhook_url == "https://chat.googleapis.com/sendto-webhook"

    def test_validate_success(self) -> None:
        config = NotificationConfig(webhook_url="https://chat.googleapis.com/valid")
        config.validate()  # エラーが発生しないこと

    def test_validate_missing_webhook_url(self) -> None:
        config = NotificationConfig()
        with pytest.raises(ConfigurationError, match="Webhook URL"):
            config.validate()

    def test_validate_invalid_webhook_url(self) -> None:
        config = NotificationConfig(webhook_url="http://insecure.example.com")
        with pytest.raises(ConfigurationError, match="https://"):
            config.validate()

    def test_validate_invalid_timeout(self) -> None:
        config = NotificationConfig(
            webhook_url="https://valid.example.com",
            timeout=0,
        )
        with pytest.raises(ConfigurationError, match="タイムアウト"):
            config.validate()

    def test_validate_invalid_log_level(self) -> None:
        config = NotificationConfig(
            webhook_url="https://valid.example.com",
            log_level="INVALID",
        )
        with pytest.raises(ConfigurationError, match="ログレベル"):
            config.validate()

    def test_from_env_invalid_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """無効なタイムアウト値はデフォルト値を使用する."""
        monkeypatch.setenv("GCHAT_TIMEOUT", "not_a_number")
        config = NotificationConfig.from_env()
        assert config.timeout == 10  # デフォルト値
