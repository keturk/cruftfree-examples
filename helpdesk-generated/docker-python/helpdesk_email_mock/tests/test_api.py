"""API endpoint tests for helpdesk.EmailMock.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_email_api_post_deliveries(client):
    """POST /v1/deliveries returns 422"""
    response = await client.post(
        "/v1/deliveries",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_email_desk_api_list_outbounds(client):
    """GET /api/v1/desk/email/outbounds returns 422"""
    response = await client.get(
        "/api/v1/desk/email/outbounds",
    )
    assert response.status_code == 422


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestEmailApiAuthAccess:
    """Test authentication and role-based access control for EmailApi."""

    async def test_email_api_post_deliveries_unauthenticated(self, unauth_client):
        """POST /v1/deliveries without auth returns 401"""
        response = await unauth_client.post(
            "/v1/deliveries",
            json={},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestEmailDeskApiAuthAccess:
    """Test authentication and role-based access control for EmailDeskApi."""

    async def test_email_desk_api_list_outbounds_unauthenticated(self, unauth_client):
        """GET /api/v1/desk/email/outbounds without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/desk/email/outbounds",
        )
        assert response.status_code == 401

    async def test_email_desk_api_list_outbounds_wrong_role(self, wrong_role_client):
        """GET /api/v1/desk/email/outbounds with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/desk/email/outbounds",
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestApiKeyVerifyAuthAccess:
    """Test authentication and role-based access control for ApiKeyVerify."""

    async def test_api_key_verify_post_email_keys_verify_unauthenticated(
        self, unauth_client
    ):
        """POST /internal/identity/api-keys/emailKeys/verify without auth returns 401"""
        response = await unauth_client.post(
            "/internal/identity/api-keys/emailKeys/verify",
            json={},
        )
        assert response.status_code == 401

    async def test_api_key_verify_post_email_keys_verify_non_service_token(
        self, wrong_role_client
    ):
        """POST /internal/identity/api-keys/emailKeys/verify with a non-service token returns 403"""
        response = await wrong_role_client.post(
            "/internal/identity/api-keys/emailKeys/verify",
            json={},
        )
        assert response.status_code == 403
