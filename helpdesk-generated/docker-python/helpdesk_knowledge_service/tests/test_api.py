"""API endpoint tests for helpdesk.KnowledgeService.

Auto-generated test suite that drives the API in-process through httpx
ASGITransport against a real database session (or a deployed service when
BASE_URL is set). Because these tests require a real database, they are
marked ``integration`` and are excluded from the database-free unit run.
Run with: pytest test_api.py -m integration
"""

import pytest


@pytest.mark.integration
async def test_help_api_get_articles(client):
    """GET /api/v1/help/articles returns 200"""
    response = await client.get(
        "/api/v1/help/articles",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_help_api_get_search_by_query(client):
    """GET /api/v1/help/search/00000000-0000-0000-0000-000000000001 returns 200"""
    response = await client.get(
        "/api/v1/help/search/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_help_api_get_articles_by_id(client):
    """GET /api/v1/help/articles/00000000-0000-0000-0000-000000000001 returns 200"""
    response = await client.get(
        "/api/v1/help/articles/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 200


@pytest.mark.integration
async def test_help_api_post_articles_by_id_vote(client):
    """POST /api/v1/help/articles/00000000-0000-0000-0000-000000000001/vote returns 422"""
    response = await client.post(
        "/api/v1/help/articles/00000000-0000-0000-0000-000000000001/vote",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_knowledge_desk_api_list_articles(client):
    """GET /api/v1/desk/articles returns 422"""
    response = await client.get(
        "/api/v1/desk/articles",
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_knowledge_desk_api_get_article(client):
    """GET /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.get(
        "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_knowledge_desk_api_create_article(client):
    """POST /api/v1/desk/articles returns 422"""
    response = await client.post(
        "/api/v1/desk/articles",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.integration
async def test_knowledge_desk_api_update_article(client):
    """PUT /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.put(
        "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
        json={},
    )
    assert response.status_code == 404


@pytest.mark.integration
async def test_knowledge_desk_api_delete_article(client):
    """DELETE /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 returns 404"""
    response = await client.delete(
        "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
    )
    assert response.status_code == 404


# --- Authentication / Authorization Tests ---


@pytest.mark.integration
class TestHelpApiAuthAccess:
    """Test authentication and role-based access control for HelpApi."""

    async def test_help_api_get_articles_public_no_auth(self, client):
        """Public GET /api/v1/help/articles without auth returns 200"""
        response = await client.get(
            "/api/v1/help/articles",
        )
        assert response.status_code == 200

    async def test_help_api_get_search_by_query_public_no_auth(self, client):
        """Public GET /api/v1/help/search/00000000-0000-0000-0000-000000000001 without auth returns 200"""
        response = await client.get(
            "/api/v1/help/search/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 200

    async def test_help_api_get_articles_by_id_public_no_auth(self, client):
        """Public GET /api/v1/help/articles/00000000-0000-0000-0000-000000000001 without auth returns 200"""
        response = await client.get(
            "/api/v1/help/articles/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 200

    async def test_help_api_post_articles_by_id_vote_public_no_auth(self, client):
        """Public POST /api/v1/help/articles/00000000-0000-0000-0000-000000000001/vote without auth returns 422"""
        response = await client.post(
            "/api/v1/help/articles/00000000-0000-0000-0000-000000000001/vote",
            json={},
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestKnowledgeDeskApiAuthAccess:
    """Test authentication and role-based access control for KnowledgeDeskApi."""

    async def test_knowledge_desk_api_list_articles_unauthenticated(
        self, unauth_client
    ):
        """GET /api/v1/desk/articles without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/desk/articles",
        )
        assert response.status_code == 401

    async def test_knowledge_desk_api_get_article_unauthenticated(self, unauth_client):
        """GET /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.get(
            "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_knowledge_desk_api_create_article_unauthenticated(
        self, unauth_client
    ):
        """POST /api/v1/desk/articles without auth returns 401"""
        response = await unauth_client.post(
            "/api/v1/desk/articles",
            json={},
        )
        assert response.status_code == 401

    async def test_knowledge_desk_api_update_article_unauthenticated(
        self, unauth_client
    ):
        """PUT /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.put(
            "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
            json={},
        )
        assert response.status_code == 401

    async def test_knowledge_desk_api_delete_article_unauthenticated(
        self, unauth_client
    ):
        """DELETE /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 without auth returns 401"""
        response = await unauth_client.delete(
            "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 401

    async def test_knowledge_desk_api_list_articles_wrong_role(self, wrong_role_client):
        """GET /api/v1/desk/articles with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/desk/articles",
        )
        assert response.status_code == 403

    async def test_knowledge_desk_api_get_article_wrong_role(self, wrong_role_client):
        """GET /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.get(
            "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403

    async def test_knowledge_desk_api_create_article_wrong_role(
        self, wrong_role_client
    ):
        """POST /api/v1/desk/articles with wrong role returns 403"""
        response = await wrong_role_client.post(
            "/api/v1/desk/articles",
            json={},
        )
        assert response.status_code == 403

    async def test_knowledge_desk_api_update_article_wrong_role(
        self, wrong_role_client
    ):
        """PUT /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.put(
            "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
            json={},
        )
        assert response.status_code == 403

    async def test_knowledge_desk_api_delete_article_wrong_role(
        self, wrong_role_client
    ):
        """DELETE /api/v1/desk/articles/00000000-0000-0000-0000-000000000001 with wrong role returns 403"""
        response = await wrong_role_client.delete(
            "/api/v1/desk/articles/00000000-0000-0000-0000-000000000001",
        )
        assert response.status_code == 403
