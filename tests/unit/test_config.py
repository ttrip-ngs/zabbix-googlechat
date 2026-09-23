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

    def test_load_priority_sendto_over_yaml(self, sample_yaml: Path) -> None:
        """URL の ALERT.SENDTO は YAML より優先される."""
        config = NotificationConfig.load(
            yaml_path=sample_yaml,
            alert_sendto="https://chat.googleapis.com/sendto-webhook",
        )
        assert config.webhook_url == "https://chat.googleapis.com/sendto-webhook"

    def test_load_priority_sendto_over_env(
        self, sample_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """URL の ALERT.SENDTO は環境変数より優先される."""
        monkeypatch.setenv("GCHAT_WEBHOOK_URL", "https://chat.googleapis.com/env-webhook")
        config = NotificationConfig.load(
            yaml_path=sample_yaml,
            alert_sendto="https://chat.googleapis.com/sendto-webhook",
        )
        assert config.webhook_url == "https://chat.googleapis.com/sendto-webhook"

    def test_load_non_url_sendto_falls_back_to_yaml(
        self, sample_yaml: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """URL でない ALERT.SENDTO(ラベル等)は無視して YAML を使い、警告を出す."""
        config = NotificationConfig.load(
            yaml_path=sample_yaml,
            alert_sendto="gchat-matsuura-gaku",
        )
        assert config.webhook_url == "https://chat.googleapis.com/v1/spaces/test"
        assert "https:// で始まらないため無視" in caplog.text
        assert "gchat-matsuura-gaku" not in caplog.text

    def test_load_http_sendto_is_ignored(self, sample_yaml: Path) -> None:
        """http:// の ALERT.SENDTO は採用しない(YAML を使う)."""
        config = NotificationConfig.load(
            yaml_path=sample_yaml,
            alert_sendto="http://chat.googleapis.com/insecure",
        )
        assert config.webhook_url == "https://chat.googleapis.com/v1/spaces/test"

    def test_load_sendto_without_yaml_and_env(self) -> None:
        """YAMLも環境変数もない場合もALERT.SENDTOを使用."""
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

    # ---- card_style のテスト ----

    def test_card_style_default(self) -> None:
        """card_style の既定値は detailed."""
        config = NotificationConfig()
        assert config.card_style == "detailed"

    def test_card_style_from_yaml(self, tmp_path: Path) -> None:
        """YAML から card_style を読み込む."""
        data = {"googlechat": {"webhook_url": "https://x", "card_style": "compact"}}
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml.dump(data), encoding="utf-8")
        config = NotificationConfig.from_yaml(yaml_file)
        assert config.card_style == "compact"

    def test_card_style_env_over_yaml(
        self, sample_yaml: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数 GCHAT_CARD_STYLE は YAML より優先される."""
        monkeypatch.setenv("GCHAT_CARD_STYLE", "text")
        config = NotificationConfig.load(yaml_path=sample_yaml)
        assert config.card_style == "text"

    def test_validate_invalid_card_style_falls_back(self) -> None:
        """不正な card_style は例外を投げず detailed にフォールバックする."""
        config = NotificationConfig(
            webhook_url="https://valid.example.com",
            card_style="bogus",
        )
        config.validate()  # 例外が発生しないこと
        assert config.card_style == "detailed"

    def test_validate_valid_card_style_preserved(self) -> None:
        """有効な card_style は validate で保持される."""
        config = NotificationConfig(
            webhook_url="https://valid.example.com",
            card_style="medium",
        )
        config.validate()
        assert config.card_style == "medium"
