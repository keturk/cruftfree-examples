"""Specification tests for helpdesk.NoticeService.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from helpdesk_notice_service.schemas.notice_db.notice import NoticeCreate
from helpdesk_notice_service.services.notice_db.notice_service import NoticeService


@pytest.mark.spec
async def test_a_new_notice_has_not_been_delivered(db_session, event_spy):
    """a new notice has not been delivered"""
    _notice_svc = NoticeService(db_session)
    created = await _notice_svc.create(
        NoticeCreate.model_validate(
            {
                "recipient": "someone@example.com",
                "subject": "Subject",
                "body": "Body",
                "noticeKey": "test-key",
            }
        )
    )
    assert created.delivered == False
    assert created.attempts == 0
