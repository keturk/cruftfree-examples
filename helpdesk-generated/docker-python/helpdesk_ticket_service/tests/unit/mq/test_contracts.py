"""Tests for event contract validation.

Auto-generated. Verifies that contract violations are detected.
"""

from __future__ import annotations

import pytest

from helpdesk_ticket_service.errors import ContractViolationError
from helpdesk_ticket_service.mq.contracts import (
    _validate_agent_replied_contract,
    _validate_response_late_contract,
    _validate_ticket_opened_contract,
    _validate_ticket_resolved_contract,
)


class TestTicketOpenedContracts:
    """Contract tests for TicketOpened."""

    @pytest.mark.cruftfree_case("pubsub_contract/mq/TicketOpened/accepts_valid_payload")
    def test_valid_payload_passes(self) -> None:
        """Valid payload passes all contract checks."""
        _validate_ticket_opened_contract(
            number="x",
            subject="test_value",
            customer_name="test_value",
            customer_email="test_value",
        )

    @pytest.mark.cruftfree_case(
        "pubsub_contract/mq/TicketOpened/0/rejects_violated_clause"
    )
    def test_violating_clause_0(self) -> None:
        """Violating 'number.length > 0' raises ContractViolationError."""
        with pytest.raises(ContractViolationError) as exc_info:
            _validate_ticket_opened_contract(
                number="",
                subject="test_value",
                customer_name="test_value",
                customer_email="test_value",
            )
        assert exc_info.value.event == "TicketOpened"
        assert exc_info.value.clause == "number.length > 0"


class TestAgentRepliedContracts:
    """Contract tests for AgentReplied."""

    @pytest.mark.cruftfree_case("pubsub_contract/mq/AgentReplied/accepts_valid_payload")
    def test_valid_payload_passes(self) -> None:
        """Valid payload passes all contract checks."""
        _validate_agent_replied_contract(
            number="test_value",
            subject="test_value",
            agent_name="test_value",
            customer_email="test_value",
            body="x",
        )

    @pytest.mark.cruftfree_case(
        "pubsub_contract/mq/AgentReplied/0/rejects_violated_clause"
    )
    def test_violating_clause_0(self) -> None:
        """Violating 'body.length > 0' raises ContractViolationError."""
        with pytest.raises(ContractViolationError) as exc_info:
            _validate_agent_replied_contract(
                number="test_value",
                subject="test_value",
                agent_name="test_value",
                customer_email="test_value",
                body="",
            )
        assert exc_info.value.event == "AgentReplied"
        assert exc_info.value.clause == "body.length > 0"


class TestTicketResolvedContracts:
    """Contract tests for TicketResolved."""

    @pytest.mark.cruftfree_case(
        "pubsub_contract/mq/TicketResolved/accepts_valid_payload"
    )
    def test_valid_payload_passes(self) -> None:
        """Valid payload passes all contract checks."""
        _validate_ticket_resolved_contract(
            number="x",
            subject="test_value",
            customer_email="test_value",
        )

    @pytest.mark.cruftfree_case(
        "pubsub_contract/mq/TicketResolved/0/rejects_violated_clause"
    )
    def test_violating_clause_0(self) -> None:
        """Violating 'number.length > 0' raises ContractViolationError."""
        with pytest.raises(ContractViolationError) as exc_info:
            _validate_ticket_resolved_contract(
                number="",
                subject="test_value",
                customer_email="test_value",
            )
        assert exc_info.value.event == "TicketResolved"
        assert exc_info.value.clause == "number.length > 0"


class TestResponseLateContracts:
    """Contract tests for ResponseLate."""

    @pytest.mark.cruftfree_case("pubsub_contract/mq/ResponseLate/accepts_valid_payload")
    def test_valid_payload_passes(self) -> None:
        """Valid payload passes all contract checks."""
        _validate_response_late_contract(
            number="x",
            subject="test_value",
            priority="test_value",
        )

    @pytest.mark.cruftfree_case(
        "pubsub_contract/mq/ResponseLate/0/rejects_violated_clause"
    )
    def test_violating_clause_0(self) -> None:
        """Violating 'number.length > 0' raises ContractViolationError."""
        with pytest.raises(ContractViolationError) as exc_info:
            _validate_response_late_contract(
                number="",
                subject="test_value",
                priority="test_value",
            )
        assert exc_info.value.event == "ResponseLate"
        assert exc_info.value.clause == "number.length > 0"
