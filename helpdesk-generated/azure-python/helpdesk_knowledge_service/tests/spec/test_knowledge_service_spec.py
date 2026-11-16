"""Specification tests for helpdesk.KnowledgeService.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from helpdesk_knowledge_service.enums.ticket_topic import TicketTopic
from helpdesk_knowledge_service.schemas.knowledge_db.article import ArticleCreate
from helpdesk_knowledge_service.services.knowledge_db.article_service import (
    ArticleService,
)


@pytest.mark.spec
async def test_a_new_article_is_a_draft(db_session):
    """a new article is a draft"""
    _article_svc = ArticleService(db_session)
    created = await _article_svc.create(
        ArticleCreate.model_validate(
            {
                "title": "Title",
                "summary": "Summary",
                "body": "Body",
                "topic": TicketTopic.billing,
            }
        )
    )
    assert created.published == False
    assert created.helpful == 0
