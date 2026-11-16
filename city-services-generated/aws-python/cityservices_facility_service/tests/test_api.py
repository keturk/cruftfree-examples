"""API endpoint tests for cityservices.FacilityService.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_facility_api_list_facilities(client):
    """GET /api/v1/facilities returns 422"""
    response = await client.get(
        "/api/v1/facilities",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_facility_api_get_map(client):
    """GET /api/v1/facilities/map returns 200"""
    response = await client.get(
        "/api/v1/facilities/map",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_facility_api_get_nearby(client):
    """GET /api/v1/facilities/nearby returns 422"""
    response = await client.get(
        "/api/v1/facilities/nearby",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_facility_api_parks(client):
    """GET /api/v1/facilities/parks returns 200"""
    response = await client.get(
        "/api/v1/facilities/parks",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_facility_api_post_by_id_operational(client):
    """POST /api/v1/facilities/00000000-0000-0000-0000-000000000001/operational returns 422"""
    response = await client.post(
        "/api/v1/facilities/00000000-0000-0000-0000-000000000001/operational",
        json={},
    )
    assert response.status_code == 422


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestFacilityApiAuthAccess:
    """Test authentication and role-based access control for FacilityApi."""

    async def test_facility_api_list_facilities_public_no_auth(self, client):
        """Public GET /api/v1/facilities without auth returns 422"""
        response = await client.get(
            "/api/v1/facilities",
        )
        assert response.status_code == 422

    async def test_facility_api_get_map_public_no_auth(self, client):
        """Public GET /api/v1/facilities/map without auth returns 200"""
        response = await client.get(
            "/api/v1/facilities/map",
        )
        assert response.status_code == 200

    async def test_facility_api_get_nearby_public_no_auth(self, client):
        """Public GET /api/v1/facilities/nearby without auth returns 422"""
        response = await client.get(
            "/api/v1/facilities/nearby",
        )
        assert response.status_code == 422

    async def test_facility_api_parks_public_no_auth(self, client):
        """Public GET /api/v1/facilities/parks without auth returns 200"""
        response = await client.get(
            "/api/v1/facilities/parks",
        )
        assert response.status_code == 200

    async def test_facility_api_post_by_id_operational_unauthenticated(
        self, unauth_client
    ):
        """POST /api/v1/facilities/00000000-0000-0000-0000-000000000001/operational without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/facilities/00000000-0000-0000-0000-000000000001/operational",
            json={},
        )
        assert response.status_code == 401

    async def test_facility_api_post_by_id_operational_wrong_role(
        self, wrong_role_client
    ):
        """POST /api/v1/facilities/00000000-0000-0000-0000-000000000001/operational with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/facilities/00000000-0000-0000-0000-000000000001/operational",
            json={},
        )
        assert response.status_code == 403
