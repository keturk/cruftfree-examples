"""Specification tests for helpdesk.TicketService.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from helpdesk_ticket_service.enums.priority import Priority
from helpdesk_ticket_service.functions import raised


@pytest.mark.spec
async def test_a_higher_priority_is_never_lower(db_session, event_spy):
    """a higher priority is never lower"""
    assert raised(Priority.low) == Priority.normal
    assert raised(Priority.normal) == Priority.high
    assert raised(Priority.high) == Priority.urgent
    assert raised(Priority.urgent) == Priority.urgent
