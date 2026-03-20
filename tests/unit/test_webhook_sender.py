"""webhook_sender.py のユニットテスト."""

import pytest
import responses as responses_lib

from zabbix_googlechat.exceptions import WebhookConnectionError, WebhookPayloadError
from zabbix_googlechat.webhook_sender import GoogleChatWebhookSender

WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/test/messages?key=xxx"
SAMPLE_PAYLOAD = {"cardsV2": [{"cardId": "test-card", "card": {"header": {"title": "Test"}}}]}


@pytest.fixture
def sender() -> GoogleChatWebhookSender:
    return GoogleChatWebhookSender(
        webhook_url=WEBHOOK_URL,
        timeout=5,
        max_retries=2,
        retry_delay=0.01,  # テスト高速化のため最小値
    )


class TestGoogleChatWebhookSender:
    @responses_lib.activate
    def test_send_success(self, sender: GoogleChatWebhookSender) -> None:
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            json={"name": "spaces/test/messages/xxx"},
            status=200,
        )
        response = sender.send(SAMPLE_PAYLOAD)
        assert response.success is True
        assert response.status_code == 200
        assert response.retry_count == 0

    @responses_lib.activate
    def test_send_400_raises_payload_error(self, sender: GoogleChatWebhookSender) -> None:
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            json={"error": {"message": "Invalid payload"}},
            status=400,
        )
        with pytest.raises(WebhookPayloadError) as exc_info:
            sender.send(SAMPLE_PAYLOAD)
        assert exc_info.value.status_code == 400

    @responses_lib.activate
    def test_send_retry_on_500(self, sender: GoogleChatWebhookSender) -> None:
        # 1回目: 500エラー
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            json={"error": "Internal Server Error"},
            status=500,
        )
        # 2回目: 成功
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            json={"name": "spaces/test/messages/xxx"},
            status=200,
        )
        response = sender.send(SAMPLE_PAYLOAD)
        assert response.success is True
        assert response.retry_count == 1

    @responses_lib.activate
    def test_send_retry_exhausted_raises_connection_error(
        self, sender: GoogleChatWebhookSender
    ) -> None:
        # 全リクエストが500エラー（max_retries=2、合計3回試みる）
        for _ in range(3):
            responses_lib.add(
                responses_lib.POST,
                WEBHOOK_URL,
                json={"error": "Service Unavailable"},
                status=503,
            )
        with pytest.raises(WebhookConnectionError, match="リトライ上限"):
            sender.send(SAMPLE_PAYLOAD)

    @responses_lib.activate
    def test_send_429_triggers_retry(self, sender: GoogleChatWebhookSender) -> None:
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            status=429,
        )
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            json={"name": "spaces/test/messages/xxx"},
            status=200,
        )
        response = sender.send(SAMPLE_PAYLOAD)
        assert response.success is True
        assert response.retry_count == 1

    @responses_lib.activate
    def test_send_connection_error_triggers_retry(self, sender: GoogleChatWebhookSender) -> None:
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            body=ConnectionError("接続エラー"),
        )
        responses_lib.add(
            responses_lib.POST,
            WEBHOOK_URL,
            json={"name": "spaces/test/messages/xxx"},
            status=200,
        )
        response = sender.send(SAMPLE_PAYLOAD)
        assert response.success is True

    def test_context_manager(self) -> None:
        with GoogleChatWebhookSender(WEBHOOK_URL) as s:
            assert s is not None
        # closeが呼ばれてもエラーにならないこと

    def test_no_retries_on_client_error(self) -> None:
        """クライアントエラー（401, 403, 404）はリトライしない."""
        for status in [401, 403, 404]:
            with responses_lib.RequestsMock() as rsps:
                rsps.add(responses_lib.POST, WEBHOOK_URL, status=status)
                with pytest.raises(WebhookPayloadError):
                    sender_local = GoogleChatWebhookSender(
                        WEBHOOK_URL, max_retries=3, retry_delay=0.01
                    )
                    sender_local.send(SAMPLE_PAYLOAD)
                # リクエストが1回しか送られていないことを確認
                assert len(rsps.calls) == 1
