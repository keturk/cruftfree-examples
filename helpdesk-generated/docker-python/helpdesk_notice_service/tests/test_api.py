"""API endpoint tests for helpdesk.NoticeService.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_notice_desk_api_list_notices(client):
    """GET /api/v1/desk/notices returns 422"""
    response = await client.get(
        "/api/v1/desk/notices",
    )
    assert response.status_code == 422


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestNoticeDeskApiAuthAccess:
    """Test authentication and role-based access control for NoticeDeskApi."""

    async def test_notice_desk_api_list_notices_unauthenticated(self, unauth_client):
        """GET /api/v1/desk/notices without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/desk/notices",
        )
        assert response.status_code == 401

    async def test_notice_desk_api_list_notices_wrong_role(self, wrong_role_client):
        """GET /api/v1/desk/notices with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/desk/notices",
        )
        assert response.status_code == 403
