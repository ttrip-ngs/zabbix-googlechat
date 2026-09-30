"""chat_api_sender.py のユニットテスト."""

import json
import logging
from pathlib import Path

import pytest
import requests
import responses as responses_lib
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from responses import matchers

from zabbix_googlechat.chat_api_sender import GoogleChatApiSender, build_message_id
from zabbix_googlechat.exceptions import ConfigurationError, WebhookPayloadError

TOKEN_URI = "https://oauth2.googleapis.com/token"
SPACE = "spaces/AAAAtest"
MESSAGES_URL = f"https://chat.googleapis.com/v1/{SPACE}/messages"
SAMPLE_PAYLOAD = {"cardsV2": [{"cardId": "test-card", "card": {"header": {"title": "Test"}}}]}


@pytest.fixture(scope="module")
def private_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


@pytest.fixture
def credentials_file(tmp_path: Path, private_key_pem: str) -> Path:
    """テスト用のサービスアカウント鍵（実在しないアカウント）."""
    data = {
        "type": "service_account",
        "project_id": "test-project",
        "private_key_id": "test-key-id",
        "private_key": private_key_pem,
        "client_email": "zabbix@test-project.iam.gserviceaccount.com",
        "client_id": "1",
        "token_uri": TOKEN_URI,
    }
    path = tmp_path / "service-account.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


@pytest.fixture
def sender(credentials_file: Path) -> GoogleChatApiSender:
    return GoogleChatApiSender(
        space=SPACE,
        credentials_file=str(credentials_file),
        timeout=5,
        max_retries=1,
        retry_delay=0.01,
    )


def _add_token_response() -> None:
    responses_lib.add(
        responses_lib.POST,
        TOKEN_URI,
        json={"access_token": "test-token", "expires_in": 3600, "token_type": "Bearer"},
    )


class TestBuildMessageId:
    def test_numeric_event_id(self) -> None:
        assert build_message_id("zbx", "12345") == "client-zbx-12345"

    def test_prefix_with_hyphen(self) -> None:
        assert build_message_id("zbx-fujisaki", "1") == "client-zbx-fujisaki-1"

    @pytest.mark.parametrize("event_id", ["", "{EVENT.ID}", "12a"])
    def test_non_numeric_event_id_returns_none(self, event_id: str) -> None:
        assert build_message_id("zbx", event_id) is None

    def test_invalid_prefix_returns_none(self) -> None:
        assert build_message_id("ZBX", "1") is None

    def test_too_long_returns_none(self) -> None:
        assert build_message_id("z" * 40, "1" * 20) is None


class TestGoogleChatApiSender:
    def test_invalid_credentials_file_raises_configuration_error(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(ConfigurationError):
            GoogleChatApiSender(space=SPACE, credentials_file=str(path))

    @responses_lib.activate
    def test_create_with_message_id(self, sender: GoogleChatApiSender) -> None:
        _add_token_response()
        responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"name": f"{SPACE}/messages/client-zbx-1"},
            match=[
                matchers.query_param_matcher({"messageId": "client-zbx-1"}),
                matchers.header_matcher({"authorization": "Bearer test-token"}),
                matchers.json_params_matcher(SAMPLE_PAYLOAD),
            ],
        )
        response = sender.create(SAMPLE_PAYLOAD, "client-zbx-1")
        assert response.success is True

    @responses_lib.activate
    def test_create_without_message_id(self, sender: GoogleChatApiSender) -> None:
        _add_token_response()
        responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"name": f"{SPACE}/messages/abc"},
            match=[matchers.query_param_matcher({})],
        )
        response = sender.create(SAMPLE_PAYLOAD, None)
        assert response.success is True

    @responses_lib.activate
    def test_create_conflict_posts_new_message(
        self, sender: GoogleChatApiSender, caplog: pytest.LogCaptureFixture
    ) -> None:
        """同じメッセージIDが既にある場合（再通知）はIDなしで投稿し、ERROR ログは出さない."""
        _add_token_response()
        responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"error": {"status": "ALREADY_EXISTS"}},
            status=409,
            match=[matchers.query_param_matcher({"messageId": "client-zbx-1"})],
        )
        new_message = responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"name": f"{SPACE}/messages/abc"},
            match=[matchers.query_param_matcher({})],
        )
        with caplog.at_level(logging.DEBUG):
            response = sender.create(SAMPLE_PAYLOAD, "client-zbx-1")
        assert response.success is True
        assert new_message.call_count == 1
        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]

    @responses_lib.activate
    def test_create_bad_request_with_id_posts_new_message(
        self, sender: GoogleChatApiSender
    ) -> None:
        """ID付き投稿が 400 の場合もIDなしで投稿し直す（ID重複が 400 で返る場合の保険）."""
        _add_token_response()
        responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"error": {"status": "INVALID_ARGUMENT"}},
            status=400,
            match=[matchers.query_param_matcher({"messageId": "client-zbx-1"})],
        )
        new_message = responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"name": f"{SPACE}/messages/abc"},
            match=[matchers.query_param_matcher({})],
        )
        response = sender.create(SAMPLE_PAYLOAD, "client-zbx-1")
        assert response.success is True
        assert new_message.call_count == 1

    @responses_lib.activate
    def test_upsert_patches_message(self, sender: GoogleChatApiSender) -> None:
        _add_token_response()
        responses_lib.add(
            responses_lib.PATCH,
            f"{MESSAGES_URL}/client-zbx-1",
            json={"name": f"{SPACE}/messages/client-zbx-1"},
            match=[
                matchers.query_param_matcher(
                    {"updateMask": "text,cardsV2", "allowMissing": "true"}
                ),
                matchers.json_params_matcher(SAMPLE_PAYLOAD),
            ],
        )
        response = sender.upsert(SAMPLE_PAYLOAD, "client-zbx-1")
        assert response.success is True

    @responses_lib.activate
    def test_forbidden_raises_payload_error(self, sender: GoogleChatApiSender) -> None:
        """Chat アプリがスペースに追加されていない場合など."""
        _add_token_response()
        responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"error": {"status": "PERMISSION_DENIED"}},
            status=403,
        )
        with pytest.raises(WebhookPayloadError) as exc_info:
            sender.create(SAMPLE_PAYLOAD, None)
        assert exc_info.value.status_code == 403

    @responses_lib.activate
    def test_token_refresh_failure_raises_payload_error(self, sender: GoogleChatApiSender) -> None:
        responses_lib.add(
            responses_lib.POST,
            TOKEN_URI,
            json={"error": "invalid_grant", "error_description": "Invalid JWT Signature."},
            status=400,
        )
        with pytest.raises(WebhookPayloadError) as exc_info:
            sender.create(SAMPLE_PAYLOAD, None)
        assert exc_info.value.status_code == 401

    @pytest.mark.parametrize("status", [400, 403, 404])
    @responses_lib.activate
    def test_upsert_failure_posts_new_message(
        self, sender: GoogleChatApiSender, status: int
    ) -> None:
        """更新が恒久エラーなら新しいメッセージとして投稿し、復旧通知を失わない."""
        _add_token_response()
        responses_lib.add(
            responses_lib.PATCH,
            f"{MESSAGES_URL}/client-zbx-1",
            json={"error": {"message": "error"}},
            status=status,
        )
        new_message = responses_lib.add(
            responses_lib.POST,
            MESSAGES_URL,
            json={"name": f"{SPACE}/messages/abc"},
            match=[matchers.query_param_matcher({})],
        )
        response = sender.upsert(SAMPLE_PAYLOAD, "client-zbx-1")
        assert response.success is True
        assert new_message.call_count == 1

    @responses_lib.activate
    def test_token_transport_error_is_retried(self, sender: GoogleChatApiSender) -> None:
        """トークン取得時のネットワーク障害はリトライする."""
        responses_lib.add(
            responses_lib.POST, TOKEN_URI, body=requests.exceptions.ConnectionError("down")
        )
        _add_token_response()
        responses_lib.add(responses_lib.POST, MESSAGES_URL, json={"name": f"{SPACE}/messages/abc"})
        response = sender.create(SAMPLE_PAYLOAD, None)
        assert response.success is True
        assert response.retry_count == 1
