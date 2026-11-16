"""API endpoint tests for cityservices.GeocoderMock.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_geocoder_api_post_geocode(client):
    """POST /v1/geocode returns 422"""
    response = await client.post(
        "/v1/geocode",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_geocoder_desk_api_list_lookups(client):
    """GET /api/v1/desk/geocoder/lookups returns 422"""
    response = await client.get(
        "/api/v1/desk/geocoder/lookups",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_geocoder_desk_api_list_known_addresses(client):
    """GET /api/v1/desk/geocoder/known_addresses returns 422"""
    response = await client.get(
        "/api/v1/desk/geocoder/known_addresses",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_geocoder_desk_api_create_known_address(client):
    """POST /api/v1/desk/geocoder/known_addresses returns 422"""
    response = await client.post(
        "/api/v1/desk/geocoder/known_addresses",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_geocoder_desk_api_delete_known_address(client):
    """DELETE /api/v1/desk/geocoder/known_addresses/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.delete(
        "/api/v1/desk/geocoder/known_addresses/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestGeocoderApiAuthAccess:
    """Test authentication and role-based access control for GeocoderApi."""

    async def test_geocoder_api_post_geocode_unauthenticated(self, unauth_client):
        """POST /v1/geocode without auth returns 401"""
        response = await unauth_client.post(
            "/v1/geocode",
            json={},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestGeocoderDeskApiAuthAccess:
    """Test authentication and role-based access control for GeocoderDeskApi."""

    async def test_geocoder_desk_api_list_lookups_unauthenticated(self, unauth_client):
        """GET /api/v1/desk/geocoder/lookups without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/desk/geocoder/lookups",
        )
        assert response.status_code == 401

    async def test_geocoder_desk_api_list_known_addresses_unauthenticated(
        self, unauth_client
    ):
        """GET /api/v1/desk/geocoder/known_addresses without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/desk/geocoder/known_addresses",
        )
        assert response.status_code == 401

    async def test_geocoder_desk_api_create_known_address_unauthenticated(
        self, unauth_client
    ):
        """POST /api/v1/desk/geocoder/known_addresses without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/desk/geocoder/known_addresses",
            json={},
        )
        assert response.status_code == 401

    async def test_geocoder_desk_api_delete_known_address_unauthenticated(
        self, unauth_client
    ):
        """DELETE /api/v1/desk/geocoder/known_addresses/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.delete(
            "/api/v1/desk/geocoder/known_addresses/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_geocoder_desk_api_list_lookups_wrong_role(self, wrong_role_client):
        """GET /api/v1/desk/geocoder/lookups with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/desk/geocoder/lookups",
        )
        assert response.status_code == 403

    async def test_geocoder_desk_api_list_known_addresses_wrong_role(
        self, wrong_role_client
    ):
        """GET /api/v1/desk/geocoder/known_addresses with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/desk/geocoder/known_addresses",
        )
        assert response.status_code == 403

    async def test_geocoder_desk_api_create_known_address_wrong_role(
        self, wrong_role_client
    ):
        """POST /api/v1/desk/geocoder/known_addresses with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/desk/geocoder/known_addresses",
            json={},
        )
        assert response.status_code == 403

    async def test_geocoder_desk_api_delete_known_address_wrong_role(
        self, wrong_role_client
    ):
        """DELETE /api/v1/desk/geocoder/known_addresses/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.delete(
            "/api/v1/desk/geocoder/known_addresses/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403


@pytest.mark.integration
class TestApiKeyVerifyAuthAccess:
    """Test authentication and role-based access control for ApiKeyVerify."""

    async def test_api_key_verify_post_geocoder_keys_verify_unauthenticated(
        self, unauth_client
    ):
        """POST /internal/identity/api-keys/geocoderKeys/verify without auth returns 401"""
        response = await unauth_client.post(
            "/internal/identity/api-keys/geocoderKeys/verify",
            json={},
        )
        assert response.status_code == 401

    async def test_api_key_verify_post_geocoder_keys_verify_non_service_token(
        self, wrong_role_client
    ):
        """POST /internal/identity/api-keys/geocoderKeys/verify with a non-service token returns 403"""
        response = await wrong_role_client.post(
            "/internal/identity/api-keys/geocoderKeys/verify",
            json={},
        )
        assert response.status_code == 403
