"""Event contract validation functions.

Auto-generated from ``ensure`` clauses in event declarations.
Each function validates preconditions before event publication.
"""

from __future__ import annotations

import logging

from helpdesk_ticket_service.errors import ContractViolationError

logger = logging.getLogger(__name__)


def _validate_ticket_opened_contract(
    number: str,
    subject: str,
    customer_name: str,
    customer_email: str,
) -> None:
    """Validate contracts for TicketOpened event."""
    if not (len(number) > 0):
        logger.error(
            "contract_violation event=%r clause=%r number=%s",
            "TicketOpened",
            "number.length > 0",
            number,
        )
        raise ContractViolationError(
            event="TicketOpened",
            clause="number.length > 0",
            actual={
                "number": number,
            },
        )


def _validate_agent_replied_contract(
    number: str,
    subject: str,
    agent_name: str,
    customer_email: str,
    body: str,
) -> None:
    """Validate contracts for AgentReplied event."""
    if not (len(body) > 0):
        logger.error(
            "contract_violation event=%r clause=%r body=%s",
            "AgentReplied",
            "body.length > 0",
            body,
        )
        raise ContractViolationError(
            event="AgentReplied",
            clause="body.length > 0",
            actual={
                "body": body,
            },
        )


def _validate_ticket_resolved_contract(
    number: str,
    subject: str,
    customer_email: str,
) -> None:
    """Validate contracts for TicketResolved event."""
    if not (len(number) > 0):
        logger.error(
            "contract_violation event=%r clause=%r number=%s",
            "TicketResolved",
            "number.length > 0",
            number,
        )
        raise ContractViolationError(
            event="TicketResolved",
            clause="number.length > 0",
            actual={
                "number": number,
            },
        )


def _validate_response_late_contract(
    number: str,
    subject: str,
    priority: str,
) -> None:
    """Validate contracts for ResponseLate event."""
    if not (len(number) > 0):
        logger.error(
            "contract_violation event=%r clause=%r number=%s",
            "ResponseLate",
            "number.length > 0",
            number,
        )
        raise ContractViolationError(
            event="ResponseLate",
            clause="number.length > 0",
            actual={
                "number": number,
            },
        )
