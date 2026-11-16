"""API endpoint tests for cityservices.SmsMock.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_sms_api_post_messages(client):
    """POST /v1/messages returns 422"""
    response = await client.post(
        "/v1/messages",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_sms_desk_api_list_sent_sms(client):
    """GET /api/v1/desk/sms/sent_sms returns 422"""
    response = await client.get(
        "/api/v1/desk/sms/sent_sms",
    )
    assert response.status_code == 422


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestSmsApiAuthAccess:
    """Test authentication and role-based access control for SmsApi."""

    async def test_sms_api_post_messages_unauthenticated(self, unauth_client):
        """POST /v1/messages without auth returns 401"""
        response = await unauth_client.post(
            "/v1/messages",
            json={},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestSmsDeskApiAuthAccess:
    """Test authentication and role-based access control for SmsDeskApi."""

    async def test_sms_desk_api_list_sent_sms_unauthenticated(self, unauth_client):
        """GET /api/v1/desk/sms/sent_sms without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/desk/sms/sent_sms",
        )
        assert response.status_code == 401

    async def test_sms_desk_api_list_sent_sms_wrong_role(self, wrong_role_client):
        """GET /api/v1/desk/sms/sent_sms with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/desk/sms/sent_sms",
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestApiKeyVerifyAuthAccess:
    """Test authentication and role-based access control for ApiKeyVerify."""

    async def test_api_key_verify_post_sms_keys_verify_unauthenticated(
        self, unauth_client
    ):
        """POST /internal/identity/api-keys/smsKeys/verify without auth returns 401"""
        response = await unauth_client.post(
            "/internal/identity/api-keys/smsKeys/verify",
            json={},
        )
        assert response.status_code == 401

    async def test_api_key_verify_post_sms_keys_verify_non_service_token(
        self, wrong_role_client
    ):
        """POST /internal/identity/api-keys/smsKeys/verify with a non-service token returns 403"""
        response = await wrong_role_client.post(
            "/internal/identity/api-keys/smsKeys/verify",
            json={},
        )
        assert response.status_code == 403
