"""設定管理モジュール."""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from zabbix_googlechat.exceptions import ConfigurationError
from zabbix_googlechat.models import DEFAULT_CARD_STYLE, CardStyle

logger = logging.getLogger(__name__)

# 環境変数名定数
_ENV_WEBHOOK_URL = "GCHAT_WEBHOOK_URL"
_ENV_ZABBIX_URL = "ZABBIX_URL"
_ENV_TIMEOUT = "GCHAT_TIMEOUT"
_ENV_MAX_RETRIES = "GCHAT_MAX_RETRIES"
_ENV_LOG_LEVEL = "LOG_LEVEL"
_ENV_LOG_FILE = "LOG_FILE"
_ENV_CARD_STYLE = "GCHAT_CARD_STYLE"

# デフォルト値
_DEFAULT_TIMEOUT = 10
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_RETRY_DELAY = 1.0
_DEFAULT_LOG_LEVEL = "INFO"


@dataclass
class NotificationConfig:
    """通知設定クラス.

    Webhook URL の優先順位（高→低）:
        1. {ALERT.SENDTO} 引数（https:// で始まる場合のみ。宛先ユーザーごとの振り分けに使う）
        2. 環境変数 GCHAT_WEBHOOK_URL
        3. config.yaml の googlechat.webhook_url
    """

    # Google Chat設定
    webhook_url: str = ""
    timeout: int = _DEFAULT_TIMEOUT
    max_retries: int = _DEFAULT_MAX_RETRIES
    retry_delay: float = _DEFAULT_RETRY_DELAY
    # メッセージスタイル（detailed / medium / compact / text）
    card_style: str = DEFAULT_CARD_STYLE

    # Zabbix設定
    zabbix_url: str = ""

    # ログ設定
    log_level: str = _DEFAULT_LOG_LEVEL
    log_file: str = ""

    # 追加設定（将来拡張用）
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env_file: str | None = None) -> NotificationConfig:
        """環境変数から設定を読み込む.

        Args:
            env_file: .envファイルのパス（省略時は自動検索）

        Returns:
            NotificationConfig インスタンス
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        config = cls()
        config.webhook_url = os.environ.get(_ENV_WEBHOOK_URL, "")
        config.zabbix_url = os.environ.get(_ENV_ZABBIX_URL, "")
        config.log_level = os.environ.get(_ENV_LOG_LEVEL, _DEFAULT_LOG_LEVEL)
        config.log_file = os.environ.get(_ENV_LOG_FILE, "")
        config.card_style = os.environ.get(_ENV_CARD_STYLE, DEFAULT_CARD_STYLE)

        timeout_str = os.environ.get(_ENV_TIMEOUT, "")
        if timeout_str:
            try:
                config.timeout = int(timeout_str)
            except ValueError:
                logger.warning(
                    "無効なタイムアウト値 '%s'、デフォルト(%d)を使用", timeout_str, _DEFAULT_TIMEOUT
                )

        max_retries_str = os.environ.get(_ENV_MAX_RETRIES, "")
        if max_retries_str:
            try:
                config.max_retries = int(max_retries_str)
            except ValueError:
                logger.warning(
                    "無効なリトライ回数 '%s'、デフォルト(%d)を使用",
                    max_retries_str,
                    _DEFAULT_MAX_RETRIES,
                )

        return config

    @classmethod
    def from_yaml(cls, path: str | Path) -> NotificationConfig:
        """YAMLファイルから設定を読み込む.

        Args:
            path: config.yamlのパス

        Returns:
            NotificationConfig インスタンス

        Raises:
            ConfigurationError: ファイルが存在しない、またはYAML形式が不正な場合
        """
        yaml_path = Path(path)
        if not yaml_path.exists():
            raise ConfigurationError(f"設定ファイルが見つかりません: {yaml_path}")

        try:
            with yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAMLパースエラー: {e}") from e

        if not isinstance(data, dict):
            raise ConfigurationError(f"設定ファイルの形式が不正です: {yaml_path}")

        config = cls()
        googlechat = data.get("googlechat", {})
        zabbix = data.get("zabbix", {})
        logging_cfg = data.get("logging", {})

        config.webhook_url = str(googlechat.get("webhook_url", ""))
        config.timeout = int(googlechat.get("timeout", _DEFAULT_TIMEOUT))
        config.max_retries = int(googlechat.get("max_retries", _DEFAULT_MAX_RETRIES))
        config.retry_delay = float(googlechat.get("retry_delay", _DEFAULT_RETRY_DELAY))
        config.card_style = str(googlechat.get("card_style", DEFAULT_CARD_STYLE))
        config.zabbix_url = str(zabbix.get("url", ""))
        config.log_level = str(logging_cfg.get("level", _DEFAULT_LOG_LEVEL))
        config.log_file = str(logging_cfg.get("file", ""))

        return config

    @classmethod
    def load(
        cls,
        yaml_path: str | Path | None = None,
        env_file: str | None = None,
        alert_sendto: str = "",
    ) -> NotificationConfig:
        """優先順位を考慮して設定を読み込む.

        優先順位（高→低）:
            1. {ALERT.SENDTO} 引数（webhook_url のみ。https:// で始まる場合に限る）
            2. 環境変数
            3. config.yaml

        {ALERT.SENDTO} を最優先にするのは、Zabbix のユーザーメディアごとに
        送信先を振り分けるため。空やラベル文字列のときは環境変数・config.yaml を使う。

        Args:
            yaml_path: config.yamlのパス
            env_file: .envファイルのパス
            alert_sendto: {ALERT.SENDTO}の値（Webhook URLとして使用）

        Returns:
            NotificationConfig インスタンス
        """
        config = cls()

        # 3. config.yamlから読み込み
        if yaml_path:
            yaml_config = cls.from_yaml(yaml_path)
            if yaml_config.webhook_url:
                config.webhook_url = yaml_config.webhook_url
            if yaml_config.zabbix_url:
                config.zabbix_url = yaml_config.zabbix_url
            config.timeout = yaml_config.timeout
            config.max_retries = yaml_config.max_retries
            config.retry_delay = yaml_config.retry_delay
            config.card_style = yaml_config.card_style
            config.log_level = yaml_config.log_level
            config.log_file = yaml_config.log_file

        # 2. 環境変数で上書き
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

        env_webhook_url = os.environ.get(_ENV_WEBHOOK_URL, "")
        if env_webhook_url:
            config.webhook_url = env_webhook_url

        env_zabbix_url = os.environ.get(_ENV_ZABBIX_URL, "")
        if env_zabbix_url:
            config.zabbix_url = env_zabbix_url

        env_log_level = os.environ.get(_ENV_LOG_LEVEL, "")
        if env_log_level:
            config.log_level = env_log_level

        env_log_file = os.environ.get(_ENV_LOG_FILE, "")
        if env_log_file:
            config.log_file = env_log_file

        env_card_style = os.environ.get(_ENV_CARD_STYLE, "")
        if env_card_style:
            config.card_style = env_card_style

        env_timeout = os.environ.get(_ENV_TIMEOUT, "")
        if env_timeout:
            with contextlib.suppress(ValueError):
                config.timeout = int(env_timeout)

        env_max_retries = os.environ.get(_ENV_MAX_RETRIES, "")
        if env_max_retries:
            with contextlib.suppress(ValueError):
                config.max_retries = int(env_max_retries)

        # 1. {ALERT.SENDTO} が URL なら最優先
        if alert_sendto.startswith("https://"):
            config.webhook_url = alert_sendto
        elif alert_sendto:
            # 値は出さない(誤入力でも key/token を含みうるため)
            logger.warning(
                "{ALERT.SENDTO} が https:// で始まらないため無視し、"
                "環境変数 / config.yaml の Webhook URL を使います"
            )

        return config

    def validate(self) -> None:
        """設定の妥当性を検証する.

        Raises:
            ConfigurationError: 必須設定が未定義または不正な値の場合
        """
        if not self.webhook_url:
            raise ConfigurationError(
                "Webhook URLが設定されていません。\n"
                "以下のいずれかで設定してください:\n"
                "  1. {ALERT.SENDTO} に Webhook URLを設定\n"
                "  2. 環境変数 GCHAT_WEBHOOK_URL\n"
                "  3. config.yaml の googlechat.webhook_url"
            )

        if not self.webhook_url.startswith("https://"):
            raise ConfigurationError(
                f"無効なWebhook URL: '{self.webhook_url}'\nURLは https:// で始まる必要があります"
            )

        if self.timeout <= 0:
            raise ConfigurationError(f"タイムアウトは正の整数である必要があります: {self.timeout}")

        if self.max_retries < 0:
            raise ConfigurationError(
                f"リトライ回数は0以上の整数である必要があります: {self.max_retries}"
            )

        valid_log_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if self.log_level.upper() not in valid_log_levels:
            raise ConfigurationError(
                f"無効なログレベル: '{self.log_level}'\n"
                f"有効な値: {', '.join(sorted(valid_log_levels))}"
            )

        # メッセージスタイルは不正値でも通知到達を優先し、警告のうえ既定へフォールバック
        valid_card_styles = {style.value for style in CardStyle}
        if self.card_style not in valid_card_styles:
            logger.warning(
                "無効なメッセージスタイル '%s'、'%s' にフォールバックします（有効な値: %s）",
                self.card_style,
                DEFAULT_CARD_STYLE,
                ", ".join(sorted(valid_card_styles)),
            )
            self.card_style = DEFAULT_CARD_STYLE
