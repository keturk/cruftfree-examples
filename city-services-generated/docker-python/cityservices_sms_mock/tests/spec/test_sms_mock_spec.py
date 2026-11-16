"""Specification tests for cityservices.SmsMock.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from cityservices_sms_mock.models.sms_db.sent_sms import SentSms
from cityservices_sms_mock.schemas.sms_db.sent_sms import SentSmsCreate
from cityservices_sms_mock.services.sms_db.sent_sms_service import SentSmsService


@pytest.mark.spec
async def test_a_repeated_idempotency_key_finds_the_first_text(db_session):
    """a repeated idempotency key finds the first text"""
    _sent_sms_svc = SentSmsService(db_session)
    first = await _sent_sms_svc.create(
        SentSmsCreate.model_validate(
            {
                "messageId": "sms_0001",
                "idempotencyKey": "receipt-1",
                "recipient": "+14155550123",
                "body": "Thanks",
            }
        )
    )
    again: SentSms | None = (
        (
            await db_session.execute(
                select(SentSms).where(SentSms.idempotency_key == "receipt-1")
            )
        )
        .scalars()
        .first()
    )
    assert again is not None
    assert again.message_id == first.message_id
