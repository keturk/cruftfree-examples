"""Tests for event contract validation.

Auto-generated. Verifies that contract violations are detected.
"""

from __future__ import annotations

import uuid

import pytest

from cityservices_request_service.enums.request_status import RequestStatus
from cityservices_request_service.errors import ContractViolationError
from cityservices_request_service.mq.contracts import (
    _validate_request_status_changed_contract,
)


class TestRequestStatusChangedContracts:
    """Contract tests for RequestStatusChanged."""

    @pytest.mark.cruftfree_case(
        "pubsub_contract/mq/RequestStatusChanged/accepts_valid_payload"
    )
    def test_valid_payload_passes(self) -> None:
        """Valid payload passes all contract checks."""
        _validate_request_status_changed_contract(
            request_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
            request_number="test_value",
            old_status=RequestStatus.open,
            new_status=RequestStatus.assigned,
        )

    @pytest.mark.cruftfree_case(
        "pubsub_contract/mq/RequestStatusChanged/0/rejects_violated_clause"
    )
    def test_violating_clause_0(self) -> None:
        """Violating 'oldStatus != newStatus' raises ContractViolationError."""
        with pytest.raises(ContractViolationError) as exc_info:
            _validate_request_status_changed_contract(
                request_id=uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
                request_number="test_value",
                old_status=RequestStatus.open,
                new_status=RequestStatus.open,
            )
        assert exc_info.value.event == "RequestStatusChanged"
        assert exc_info.value.clause == "oldStatus != newStatus"
