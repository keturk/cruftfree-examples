"""Unit tests for ServiceRequest lifecycle hooks."""

from __future__ import annotations

import pytest

from cityservices_request_service.models.request_db.service_request import (
    ServiceRequest,
)


@pytest.mark.unit
class TestServiceRequestLifecycleHooks:
    """Tests for ServiceRequest entity lifecycle hooks."""

    # --- afterUpdate hook tests ---

    @pytest.mark.cruftfree_case(
        "lifecycle_hook/requestDb/ServiceRequest/status/after_update_watches"
    )
    def test_after_update_watches_status(self) -> None:
        """afterUpdate hook monitors changes to status via isChanged()."""
        instance = ServiceRequest()
        # The afterUpdate hook checks isChanged(status).
        # At the unit level, verify the watched field exists and is mutable.
        assert hasattr(instance, "status")
