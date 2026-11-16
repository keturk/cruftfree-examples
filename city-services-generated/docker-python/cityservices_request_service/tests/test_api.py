"""API endpoint tests for cityservices.RequestService.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_report_api_post_endpoint(client):
    """POST /api/v1/reports returns 422"""
    response = await client.post(
        "/api/v1/reports",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_report_api_get_track_by_request_number(client):
    """GET /api/v1/reports/track/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.get(
        "/api/v1/reports/track/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_report_api_get_nearby(client):
    """GET /api/v1/reports/nearby returns 422"""
    response = await client.get(
        "/api/v1/reports/nearby",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_queue_api_list_service_requests(client):
    """GET /api/v1/queue/requests/service_requests returns 422"""
    response = await client.get(
        "/api/v1/queue/requests/service_requests",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_queue_api_get_summary(client):
    """GET /api/v1/queue/requests/summary returns 200"""
    response = await client.get(
        "/api/v1/queue/requests/summary",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_queue_api_get_map(client):
    """GET /api/v1/queue/requests/map returns 200"""
    response = await client.get(
        "/api/v1/queue/requests/map",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_queue_api_get_by_id(client):
    """GET /api/v1/queue/requests/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.get(
        "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_queue_api_get_by_id_history(client):
    """GET /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/history returns 200"""
    response = await client.get(
        "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/history",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_queue_api_post_by_id_assign(client):
    """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/assign returns 404"""
    response = await client.post(
        "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/assign",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_queue_api_post_by_id_start(client):
    """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/start returns 404"""
    response = await client.post(
        "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/start",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_queue_api_post_by_id_resolve(client):
    """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/resolve returns 404"""
    response = await client.post(
        "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/resolve",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_queue_api_post_by_id_close(client):
    """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/close returns 404"""
    response = await client.post(
        "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/close",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_queue_api_post_by_id_priority(client):
    """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/priority returns 422"""
    response = await client.post(
        "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/priority",
        json={},
    )
    assert response.status_code == 422


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestReportApiAuthAccess:
    """Test authentication and role-based access control for ReportApi."""

    async def test_report_api_post_endpoint_public_no_auth(self, client):
        """Public POST /api/v1/reports without auth returns 422"""
        response = await client.post(
            "/api/v1/reports",
            json={},
        )
        assert response.status_code == 422

    async def test_report_api_get_track_by_request_number_public_no_auth(self, client):
        """Public GET /api/v1/reports/track/00000000-0000-0000-0000-000000000001 without auth returns 404"""
        response = await client.get(
            "/api/v1/reports/track/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 404

    async def test_report_api_get_nearby_public_no_auth(self, client):
        """Public GET /api/v1/reports/nearby without auth returns 422"""
        response = await client.get(
            "/api/v1/reports/nearby",
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestQueueApiAuthAccess:
    """Test authentication and role-based access control for QueueApi."""

    async def test_queue_api_list_service_requests_unauthenticated(self, unauth_client):
        """GET /api/v1/queue/requests/service_requests without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/queue/requests/service_requests",
        )
        assert response.status_code == 401

    async def test_queue_api_get_summary_unauthenticated(self, unauth_client):
        """GET /api/v1/queue/requests/summary without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/queue/requests/summary",
        )
        assert response.status_code == 401

    async def test_queue_api_get_map_unauthenticated(self, unauth_client):
        """GET /api/v1/queue/requests/map without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/queue/requests/map",
        )
        assert response.status_code == 401

    async def test_queue_api_get_by_id_unauthenticated(self, unauth_client):
        """GET /api/v1/queue/requests/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_queue_api_get_by_id_history_unauthenticated(self, unauth_client):
        """GET /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/history without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/history",
        )
        assert response.status_code == 401

    async def test_queue_api_post_by_id_assign_unauthenticated(self, unauth_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/assign without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/assign",
            json={},
        )
        assert response.status_code == 401

    async def test_queue_api_post_by_id_start_unauthenticated(self, unauth_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/start without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/start",
            json={},
        )
        assert response.status_code == 401

    async def test_queue_api_post_by_id_resolve_unauthenticated(self, unauth_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/resolve without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/resolve",
            json={},
        )
        assert response.status_code == 401

    async def test_queue_api_post_by_id_close_unauthenticated(self, unauth_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/close without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/close",
            json={},
        )
        assert response.status_code == 401

    async def test_queue_api_post_by_id_priority_unauthenticated(self, unauth_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/priority without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/priority",
            json={},
        )
        assert response.status_code == 401

    async def test_queue_api_list_service_requests_wrong_role(self, wrong_role_client):
        """GET /api/v1/queue/requests/service_requests with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/queue/requests/service_requests",
        )
        assert response.status_code == 403

    async def test_queue_api_get_summary_wrong_role(self, wrong_role_client):
        """GET /api/v1/queue/requests/summary with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/queue/requests/summary",
        )
        assert response.status_code == 403

    async def test_queue_api_get_map_wrong_role(self, wrong_role_client):
        """GET /api/v1/queue/requests/map with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/queue/requests/map",
        )
        assert response.status_code == 403

    async def test_queue_api_get_by_id_wrong_role(self, wrong_role_client):
        """GET /api/v1/queue/requests/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403

    async def test_queue_api_get_by_id_history_wrong_role(self, wrong_role_client):
        """GET /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/history with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/history",
        )
        assert response.status_code == 403

    async def test_queue_api_post_by_id_assign_wrong_role(self, wrong_role_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/assign with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/assign",
            json={},
        )
        assert response.status_code == 403

    async def test_queue_api_post_by_id_start_wrong_role(self, wrong_role_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/start with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/start",
            json={},
        )
        assert response.status_code == 403

    async def test_queue_api_post_by_id_resolve_wrong_role(self, wrong_role_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/resolve with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/resolve",
            json={},
        )
        assert response.status_code == 403

    async def test_queue_api_post_by_id_close_wrong_role(self, wrong_role_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/close with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/close",
            json={},
        )
        assert response.status_code == 403

    async def test_queue_api_post_by_id_priority_wrong_role(self, wrong_role_client):
        """POST /api/v1/queue/requests/00000000-0000-0000-0000-000000000001/priority with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/queue/requests/00000000-0000-0000-0000-000000000001/priority",
            json={},
        )
        assert response.status_code == 403
