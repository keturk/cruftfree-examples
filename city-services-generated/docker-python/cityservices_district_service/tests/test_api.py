"""API endpoint tests for cityservices.DistrictService.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_district_api_list_districts(client):
    """GET /api/v1/districts returns 422"""
    response = await client.get(
        "/api/v1/districts",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_district_api_get_zoning(client):
    """GET /api/v1/districts/zoning returns 422"""
    response = await client.get(
        "/api/v1/districts/zoning",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_district_api_get_facts(client):
    """GET /api/v1/districts/facts returns 200"""
    response = await client.get(
        "/api/v1/districts/facts",
    )
    assert response.status_code == 200


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestDistrictApiAuthAccess:
    """Test authentication and role-based access control for DistrictApi."""

    async def test_district_api_list_districts_public_no_auth(self, client):
        """Public GET /api/v1/districts without auth returns 422"""
        response = await client.get(
            "/api/v1/districts",
        )
        assert response.status_code == 422

    async def test_district_api_get_zoning_public_no_auth(self, client):
        """Public GET /api/v1/districts/zoning without auth returns 422"""
        response = await client.get(
            "/api/v1/districts/zoning",
        )
        assert response.status_code == 422

    async def test_district_api_get_for_location_unauthenticated(self, unauth_client):
        """GET /api/v1/districts/for-location without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/districts/for-location",
        )
        assert response.status_code == 401

    async def test_district_api_get_facts_unauthenticated(self, unauth_client):
        """GET /api/v1/districts/facts without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/districts/facts",
        )
        assert response.status_code == 401

    async def test_district_api_get_facts_wrong_role(self, wrong_role_client):
        """GET /api/v1/districts/facts with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/districts/facts",
        )
        assert response.status_code == 403

    async def test_district_api_get_for_location_non_service_token(
        self, wrong_role_client
    ):
        """GET /api/v1/districts/for-location with a non-service token returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/districts/for-location",
        )
        assert response.status_code == 403
