"""Specification tests for helpdesk.EmailMock.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from helpdesk_email_mock.constants import BOUNCING_DOMAIN


@pytest.mark.spec
async def test_an_address_at_the_bouncing_domain_is_known(db_session):
    """an address at the bouncing domain is known"""
    assert "someone@bounce.example.com".endswith(BOUNCING_DOMAIN)
    assert not "someone@example.com".endswith(BOUNCING_DOMAIN)
