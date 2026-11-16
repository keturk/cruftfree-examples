"""API endpoint tests for helpdesk.TicketService.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_ticket_api_get_endpoint(client):
    """GET /api/v1/tickets returns 200"""
    response = await client.get(
        "/api/v1/tickets",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_ticket_api_get_by_id(client):
    """GET /api/v1/tickets/00000000-0000-0000-0000-000000000001 returns 200"""
    response = await client.get(
        "/api/v1/tickets/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_ticket_api_post_endpoint(client):
    """POST /api/v1/tickets returns 422"""
    response = await client.post(
        "/api/v1/tickets",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_ticket_api_post_reply(client):
    """POST /api/v1/tickets/reply returns 422"""
    response = await client.post(
        "/api/v1/tickets/reply",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_ticket_api_post_by_id_rate(client):
    """POST /api/v1/tickets/00000000-0000-0000-0000-000000000001/rate returns 422"""
    response = await client.post(
        "/api/v1/tickets/00000000-0000-0000-0000-000000000001/rate",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_agent_api_list_tickets(client):
    """GET /api/v1/agent/tickets returns 422"""
    response = await client.get(
        "/api/v1/agent/tickets",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_agent_api_list_saved_replies(client):
    """GET /api/v1/agent/saved_replies returns 422"""
    response = await client.get(
        "/api/v1/agent/saved_replies",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_agent_api_get_saved_reply(client):
    """GET /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.get(
        "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_agent_api_create_saved_reply(client):
    """POST /api/v1/agent/saved_replies returns 422"""
    response = await client.post(
        "/api/v1/agent/saved_replies",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_agent_api_update_saved_reply(client):
    """PUT /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.put(
        "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_agent_api_delete_saved_reply(client):
    """DELETE /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.delete(
        "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_agent_api_get_reply_choices(client):
    """GET /api/v1/agent/reply-choices returns 200"""
    response = await client.get(
        "/api/v1/agent/reply-choices",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_agent_api_get_queue(client):
    """GET /api/v1/agent/queue returns 200"""
    response = await client.get(
        "/api/v1/agent/queue",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_agent_api_get_mine(client):
    """GET /api/v1/agent/mine returns 200"""
    response = await client.get(
        "/api/v1/agent/mine",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_agent_api_get_threads_by_id(client):
    """GET /api/v1/agent/threads/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.get(
        "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_agent_api_post_threads_by_id_claim(client):
    """POST /api/v1/agent/threads/00000000-0000-0000-0000-000000000001/claim returns 404"""
    response = await client.post(
        "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001/claim",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_agent_api_post_reply(client):
    """POST /api/v1/agent/reply returns 422"""
    response = await client.post(
        "/api/v1/agent/reply",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_agent_api_post_note(client):
    """POST /api/v1/agent/note returns 422"""
    response = await client.post(
        "/api/v1/agent/note",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_agent_api_post_threads_by_id_move(client):
    """POST /api/v1/agent/threads/00000000-0000-0000-0000-000000000001/move returns 422"""
    response = await client.post(
        "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001/move",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_agent_api_get_summary(client):
    """GET /api/v1/agent/summary returns 200"""
    response = await client.get(
        "/api/v1/agent/summary",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_agent_api_get_volume(client):
    """GET /api/v1/agent/volume returns 200"""
    response = await client.get(
        "/api/v1/agent/volume",
    )
    assert response.status_code == 200


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestTicketApiAuthAccess:
    """Test authentication and role-based access control for TicketApi."""

    async def test_ticket_api_get_endpoint_unauthenticated(self, unauth_client):
        """GET /api/v1/tickets without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/tickets",
        )
        assert response.status_code == 401

    async def test_ticket_api_get_by_id_unauthenticated(self, unauth_client):
        """GET /api/v1/tickets/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/tickets/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_ticket_api_post_endpoint_unauthenticated(self, unauth_client):
        """POST /api/v1/tickets without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/tickets",
            json={},
        )
        assert response.status_code == 401

    async def test_ticket_api_post_reply_unauthenticated(self, unauth_client):
        """POST /api/v1/tickets/reply without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/tickets/reply",
            json={},
        )
        assert response.status_code == 401

    async def test_ticket_api_post_by_id_rate_unauthenticated(self, unauth_client):
        """POST /api/v1/tickets/00000000-0000-0000-0000-000000000001/rate without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/tickets/00000000-0000-0000-0000-000000000001/rate",
            json={},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestAgentApiAuthAccess:
    """Test authentication and role-based access control for AgentApi."""

    async def test_agent_api_list_tickets_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/tickets without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/tickets",
        )
        assert response.status_code == 401

    async def test_agent_api_list_saved_replies_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/saved_replies without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/saved_replies",
        )
        assert response.status_code == 401

    async def test_agent_api_get_saved_reply_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_agent_api_create_saved_reply_unauthenticated(self, unauth_client):
        """POST /api/v1/agent/saved_replies without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/agent/saved_replies",
            json={},
        )
        assert response.status_code == 401

    async def test_agent_api_update_saved_reply_unauthenticated(self, unauth_client):
        """PUT /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.put(
            "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
            json={},
        )
        assert response.status_code == 401

    async def test_agent_api_delete_saved_reply_unauthenticated(self, unauth_client):
        """DELETE /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.delete(
            "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_agent_api_get_reply_choices_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/reply-choices without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/reply-choices",
        )
        assert response.status_code == 401

    async def test_agent_api_get_queue_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/queue without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/queue",
        )
        assert response.status_code == 401

    async def test_agent_api_get_mine_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/mine without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/mine",
        )
        assert response.status_code == 401

    async def test_agent_api_get_threads_by_id_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/threads/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_agent_api_post_threads_by_id_claim_unauthenticated(
        self, unauth_client
    ):
        """POST /api/v1/agent/threads/00000000-0000-0000-0000-000000000001/claim without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001/claim",
            json={},
        )
        assert response.status_code == 401

    async def test_agent_api_post_reply_unauthenticated(self, unauth_client):
        """POST /api/v1/agent/reply without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/agent/reply",
            json={},
        )
        assert response.status_code == 401

    async def test_agent_api_post_note_unauthenticated(self, unauth_client):
        """POST /api/v1/agent/note without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/agent/note",
            json={},
        )
        assert response.status_code == 401

    async def test_agent_api_post_threads_by_id_move_unauthenticated(
        self, unauth_client
    ):
        """POST /api/v1/agent/threads/00000000-0000-0000-0000-000000000001/move without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001/move",
            json={},
        )
        assert response.status_code == 401

    async def test_agent_api_get_summary_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/summary without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/summary",
        )
        assert response.status_code == 401

    async def test_agent_api_get_volume_unauthenticated(self, unauth_client):
        """GET /api/v1/agent/volume without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/agent/volume",
        )
        assert response.status_code == 401

    async def test_agent_api_list_tickets_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/tickets with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/tickets",
        )
        assert response.status_code == 403

    async def test_agent_api_list_saved_replies_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/saved_replies with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/saved_replies",
        )
        assert response.status_code == 403

    async def test_agent_api_get_saved_reply_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403

    async def test_agent_api_create_saved_reply_wrong_role(self, wrong_role_client):
        """POST /api/v1/agent/saved_replies with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/agent/saved_replies",
            json={},
        )
        assert response.status_code == 403

    async def test_agent_api_update_saved_reply_wrong_role(self, wrong_role_client):
        """PUT /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.put(
            "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
            json={},
        )
        assert response.status_code == 403

    async def test_agent_api_delete_saved_reply_wrong_role(self, wrong_role_client):
        """DELETE /api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.delete(
            "/api/v1/agent/saved_replies/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403

    async def test_agent_api_get_reply_choices_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/reply-choices with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/reply-choices",
        )
        assert response.status_code == 403

    async def test_agent_api_get_queue_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/queue with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/queue",
        )
        assert response.status_code == 403

    async def test_agent_api_get_mine_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/mine with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/mine",
        )
        assert response.status_code == 403

    async def test_agent_api_get_threads_by_id_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/threads/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403

    async def test_agent_api_post_threads_by_id_claim_wrong_role(
        self, wrong_role_client
    ):
        """POST /api/v1/agent/threads/00000000-0000-0000-0000-000000000001/claim with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001/claim",
            json={},
        )
        assert response.status_code == 403

    async def test_agent_api_post_reply_wrong_role(self, wrong_role_client):
        """POST /api/v1/agent/reply with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/agent/reply",
            json={},
        )
        assert response.status_code == 403

    async def test_agent_api_post_note_wrong_role(self, wrong_role_client):
        """POST /api/v1/agent/note with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/agent/note",
            json={},
        )
        assert response.status_code == 403

    async def test_agent_api_post_threads_by_id_move_wrong_role(
        self, wrong_role_client
    ):
        """POST /api/v1/agent/threads/00000000-0000-0000-0000-000000000001/move with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/agent/threads/00000000-0000-0000-0000-000000000001/move",
            json={},
        )
        assert response.status_code == 403

    async def test_agent_api_get_summary_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/summary with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/summary",
        )
        assert response.status_code == 403

    async def test_agent_api_get_volume_wrong_role(self, wrong_role_client):
        """GET /api/v1/agent/volume with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/agent/volume",
        )
        assert response.status_code == 403
