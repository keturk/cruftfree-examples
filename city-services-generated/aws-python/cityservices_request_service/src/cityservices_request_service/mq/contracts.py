"""Event contract validation functions.

Auto-generated from ``ensure`` clauses in event declarations.
Each function validates preconditions before event publication.
"""

from __future__ import annotations

import logging
import uuid

from prometheus_client import Counter

from cityservices_request_service.enums.request_status import RequestStatus
from cityservices_request_service.errors import ContractViolationError

logger = logging.getLogger(__name__)

CONTRACT_VIOLATION_COUNTER = Counter(
    "mq_contract_violations_total",
    "Number of event contract violations",
    ["event", "clause"],
)


def _validate_request_status_changed_contract(
    request_id: uuid.UUID,
    request_number: str,
    old_status: RequestStatus,
    new_status: RequestStatus,
) -> None:
    """Validate contracts for RequestStatusChanged event."""
    if not (old_status != new_status):
        logger.error(
            "contract_violation event=%r clause=%r newStatus=%s oldStatus=%s",
            "RequestStatusChanged",
            "oldStatus != newStatus",
            new_status,
            old_status,
        )
        CONTRACT_VIOLATION_COUNTER.labels(
            event="RequestStatusChanged",
            clause="oldStatus != newStatus",
        ).inc()
        raise ContractViolationError(
            event="RequestStatusChanged",
            clause="oldStatus != newStatus",
            actual={
                "newStatus": new_status,
                "oldStatus": old_status,
            },
        )
