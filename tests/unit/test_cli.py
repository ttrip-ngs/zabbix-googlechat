"""cli.py のユニットテスト."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from zabbix_googlechat.cli import (
    _ENV_CONFIG_PATH,
    EXIT_CONFIG_ERROR,
    EXIT_PARSE_ERROR,
    EXIT_SEND_ERROR,
    EXIT_SUCCESS,
    EXIT_UNEXPECTED_ERROR,
    _find_config_path,
    main,
    setup_logging,
)
from zabbix_googlechat.config import NotificationConfig

# ---- _find_config_path() のテスト ----


class TestFindConfigPath:
    def test_env_var_specified_and_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数で指定したパスが存在する場合、そのパスを返す."""
        config_file = tmp_path / "custom_config.yaml"
        config_file.write_text("googlechat:\n  webhook_url: ''\n", encoding="utf-8")
        monkeypatch.setenv(_ENV_CONFIG_PATH, str(config_file))

        result = _find_config_path()
        assert result == config_file

    def test_env_var_specified_but_not_exists(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """環境変数で指定したパスが存在しない場合、None を返す."""
        monkeypatch.setenv(_ENV_CONFIG_PATH, "/nonexistent/path/config.yaml")

        result = _find_config_path()
        assert result is None

    def test_env_var_not_set_fhs_path_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数なし、FHS標準パスが存在する場合、FHSパスを返す."""
        monkeypatch.delenv(_ENV_CONFIG_PATH, raising=False)

        # _FHS_CONFIG_PATH の存在をモック
        with patch("zabbix_googlechat.cli._FHS_CONFIG_PATH") as mock_fhs:
            mock_fhs.exists.return_value = True
            mock_fhs.__eq__ = lambda self, other: str(self) == str(other)
            result = _find_config_path()
            assert result == mock_fhs

    def test_env_var_not_set_local_path_exists(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数なし、FHSパスなし、ローカルパスが存在する場合、ローカルパスを返す."""
        monkeypatch.delenv(_ENV_CONFIG_PATH, raising=False)

        # FHSパスは存在しない、ローカルパスのみ存在
        with patch("zabbix_googlechat.cli._FHS_CONFIG_PATH") as mock_fhs:
            mock_fhs.exists.return_value = False
            with patch("zabbix_googlechat.cli._LOCAL_CONFIG_PATH") as mock_local:
                mock_local.exists.return_value = True
                result = _find_config_path()
                assert result == mock_local

    def test_no_config_file_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """環境変数なし、どのパスも存在しない場合、None を返す."""
        monkeypatch.delenv(_ENV_CONFIG_PATH, raising=False)

        with patch("zabbix_googlechat.cli._FHS_CONFIG_PATH") as mock_fhs:
            mock_fhs.exists.return_value = False
            with patch("zabbix_googlechat.cli._LOCAL_CONFIG_PATH") as mock_local:
                mock_local.exists.return_value = False
                result = _find_config_path()
                assert result is None

    def test_env_var_takes_precedence_over_fhs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """環境変数指定がFHSパスより優先される."""
        config_file = tmp_path / "env_config.yaml"
        config_file.write_text("googlechat:\n  webhook_url: ''\n", encoding="utf-8")
        monkeypatch.setenv(_ENV_CONFIG_PATH, str(config_file))

        # FHSパスも存在すると仮定
        with patch("zabbix_googlechat.cli._FHS_CONFIG_PATH") as mock_fhs:
            mock_fhs.exists.return_value = True
            result = _find_config_path()
            # 環境変数のパスが返るべき
            assert result == config_file


# ---- setup_logging() のテスト ----


class TestSetupLogging:
    def test_setup_with_stderr_only(self) -> None:
        """log_file なしの場合、標準エラー出力ハンドラのみ設定される."""
        config = NotificationConfig(webhook_url="https://example.com", log_level="DEBUG")
        # エラーが発生しないことを確認
        setup_logging(config)

    def test_setup_with_log_file(self, tmp_path: Path) -> None:
        """log_file ありの場合、ファイルハンドラが追加される."""
        log_file = tmp_path / "test.log"
        config = NotificationConfig(
            webhook_url="https://example.com",
            log_level="INFO",
            log_file=str(log_file),
        )
        setup_logging(config)
        assert log_file.exists()

    def test_setup_with_invalid_log_file(self, capsys: pytest.CaptureFixture[str]) -> None:
        """log_file が開けない場合、警告を出して続行する."""
        config = NotificationConfig(
            webhook_url="https://example.com",
            log_level="INFO",
            log_file="/nonexistent_dir/test.log",
        )
        # エラーが発生しないこと（警告を出して続行）
        setup_logging(config)
        captured = capsys.readouterr()
        assert "警告" in captured.err


# ---- main() のテスト ----


def _make_config_yaml(
    tmp_path: Path, webhook_url: str = "https://chat.googleapis.com/valid"
) -> Path:
    """テスト用 config.yaml を作成するヘルパー."""
    data = {
        "googlechat": {"webhook_url": webhook_url},
        "zabbix": {"url": "https://zabbix.example.com"},
        "logging": {"level": "INFO"},
    }
    yaml_file = tmp_path / "config.yaml"
    yaml_file.write_text(yaml.dump(data), encoding="utf-8")
    return yaml_file


class TestMain:
    # 共通テスト用 argv
    _VALID_ARGV = [
        "",
        "テスト通知",
        "ALERT_TYPE=PROBLEM\nHOST_NAME=test-server\nTRIGGER_NAME=テスト\nTRIGGER_SEVERITY=High\nEVENT_ID=1\nEVENT_DATE=2026.01.01\nEVENT_TIME=00:00:00",
    ]

    def test_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """正常系: 設定OK・送信成功."""
        yaml_path = _make_config_yaml(tmp_path)
        monkeypatch.setenv(_ENV_CONFIG_PATH, str(yaml_path))
        monkeypatch.setattr("sys.argv", ["prog"] + self._VALID_ARGV)

        mock_response = MagicMock()
        mock_response.retry_count = 0
        mock_response.elapsed_ms = 50.0

        with patch("zabbix_googlechat.cli.GoogleChatWebhookSender") as mock_sender_cls:
            mock_sender = MagicMock()
            mock_sender.__enter__ = MagicMock(return_value=mock_sender)
            mock_sender.__exit__ = MagicMock(return_value=False)
            mock_sender.send.return_value = mock_response
            mock_sender_cls.return_value = mock_sender

            result = main()

        assert result == EXIT_SUCCESS

    def test_parse_error_insufficient_args(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """異常系: 引数が不足している場合、EXIT_PARSE_ERROR を返す."""
        monkeypatch.setattr("sys.argv", ["prog", "only_one_arg"])

        result = main()
        assert result == EXIT_PARSE_ERROR

    def test_config_error_missing_webhook_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """異常系: Webhook URL が未設定の場合、EXIT_CONFIG_ERROR を返す."""
        monkeypatch.delenv("GCHAT_WEBHOOK_URL", raising=False)
        monkeypatch.setattr("sys.argv", ["prog"] + self._VALID_ARGV)

        with patch("zabbix_googlechat.cli._find_config_path", return_value=None):
            result = main()

        assert result == EXIT_CONFIG_ERROR

    def test_send_error_webhook_payload_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """異常系: Webhook ペイロードエラーの場合、EXIT_SEND_ERROR を返す."""
        from zabbix_googlechat.exceptions import WebhookPayloadError

        yaml_path = _make_config_yaml(tmp_path)
        monkeypatch.setenv(_ENV_CONFIG_PATH, str(yaml_path))
        monkeypatch.setattr("sys.argv", ["prog"] + self._VALID_ARGV)

        with patch("zabbix_googlechat.cli.GoogleChatWebhookSender") as mock_sender_cls:
            mock_sender = MagicMock()
            mock_sender.__enter__ = MagicMock(return_value=mock_sender)
            mock_sender.__exit__ = MagicMock(return_value=False)
            mock_sender.send.side_effect = WebhookPayloadError("HTTP 401", status_code=401)
            mock_sender_cls.return_value = mock_sender

            result = main()

        assert result == EXIT_SEND_ERROR

    def test_send_error_webhook_connection_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """異常系: Webhook 接続エラーの場合、EXIT_SEND_ERROR を返す."""
        from zabbix_googlechat.exceptions import WebhookConnectionError

        yaml_path = _make_config_yaml(tmp_path)
        monkeypatch.setenv(_ENV_CONFIG_PATH, str(yaml_path))
        monkeypatch.setattr("sys.argv", ["prog"] + self._VALID_ARGV)

        with patch("zabbix_googlechat.cli.GoogleChatWebhookSender") as mock_sender_cls:
            mock_sender = MagicMock()
            mock_sender.__enter__ = MagicMock(return_value=mock_sender)
            mock_sender.__exit__ = MagicMock(return_value=False)
            mock_sender.send.side_effect = WebhookConnectionError("接続失敗", retry_count=3)
            mock_sender_cls.return_value = mock_sender

            result = main()

        assert result == EXIT_SEND_ERROR

    def test_unexpected_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """異常系: 予期しないエラーの場合、EXIT_UNEXPECTED_ERROR を返す."""
        yaml_path = _make_config_yaml(tmp_path)
        monkeypatch.setenv(_ENV_CONFIG_PATH, str(yaml_path))
        monkeypatch.setattr("sys.argv", ["prog"] + self._VALID_ARGV)

        with patch("zabbix_googlechat.cli.GoogleChatWebhookSender") as mock_sender_cls:
            mock_sender = MagicMock()
            mock_sender.__enter__ = MagicMock(return_value=mock_sender)
            mock_sender.__exit__ = MagicMock(return_value=False)
            mock_sender.send.side_effect = RuntimeError("予期しないエラー")
            mock_sender_cls.return_value = mock_sender

            result = main()

        assert result == EXIT_UNEXPECTED_ERROR

    def test_env_only_no_config_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """正常系: config.yaml なし、環境変数のみで動作する."""
        monkeypatch.setenv("GCHAT_WEBHOOK_URL", "https://chat.googleapis.com/env-webhook")
        monkeypatch.setattr("sys.argv", ["prog"] + self._VALID_ARGV)

        mock_response = MagicMock()
        mock_response.retry_count = 0
        mock_response.elapsed_ms = 50.0

        with (
            patch("zabbix_googlechat.cli._find_config_path", return_value=None),
            patch("zabbix_googlechat.cli.GoogleChatWebhookSender") as mock_sender_cls,
        ):
            mock_sender = MagicMock()
            mock_sender.__enter__ = MagicMock(return_value=mock_sender)
            mock_sender.__exit__ = MagicMock(return_value=False)
            mock_sender.send.return_value = mock_response
            mock_sender_cls.return_value = mock_sender

            result = main()

        assert result == EXIT_SUCCESS

    def test_zabbix_url_supplement_from_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """正常系: イベントの zabbix_url が空の場合、設定ファイルの URL で補完される."""
        yaml_path = _make_config_yaml(tmp_path)
        monkeypatch.setenv(_ENV_CONFIG_PATH, str(yaml_path))
        monkeypatch.setattr("sys.argv", ["prog"] + self._VALID_ARGV)

        captured_events = []

        def capture_builder(event: object) -> MagicMock:
            captured_events.append(event)
            mock = MagicMock()
            mock.build.return_value = {"cardsV2": [{"cardId": "test"}]}
            return mock

        mock_response = MagicMock()
        mock_response.retry_count = 0
        mock_response.elapsed_ms = 50.0

        with (
            patch("zabbix_googlechat.cli.GoogleChatCardBuilder", side_effect=capture_builder),
            patch("zabbix_googlechat.cli.GoogleChatWebhookSender") as mock_sender_cls,
        ):
            mock_sender = MagicMock()
            mock_sender.__enter__ = MagicMock(return_value=mock_sender)
            mock_sender.__exit__ = MagicMock(return_value=False)
            mock_sender.send.return_value = mock_response
            mock_sender_cls.return_value = mock_sender

            result = main()

        assert result == EXIT_SUCCESS
        assert len(captured_events) == 1
        event = captured_events[0]
        # config.yaml の zabbix_url が補完されていること
        assert event.zabbix_url == "https://zabbix.example.com"
