"""Specification tests for cityservices.RequestService.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from cityservices_request_service.enums.request_category import RequestCategory
from cityservices_request_service.enums.request_status import RequestStatus
from cityservices_request_service.functions import generate_request_number
from cityservices_request_service.schemas.request_db.service_request import (
    ServiceRequestCreate,
    ServiceRequestUpdate,
)
from cityservices_request_service.services.request_db.service_request_service import (
    ServiceRequestService,
)


@pytest.mark.spec
async def test_a_new_request_is_open_and_waits_for_a_location(db_session, event_spy):
    """a new request is open and waits for a location"""
    _service_request_svc = ServiceRequestService(db_session)
    request = await _service_request_svc.create(
        ServiceRequestCreate.model_validate(
            {
                "requestNumber": generate_request_number(),
                "title": "Pothole on Harbor Street",
                "description": "Deep enough to hurt a bicycle wheel",
                "category": RequestCategory.pothole,
                "address": "12 Harbor Street",
            }
        )
    )
    assert request.status == RequestStatus.open
    assert request.needs_location


@pytest.mark.spec
async def test_changing_a_request_s_status_announces_it(db_session, event_spy):
    """changing a request's status announces it"""
    _service_request_svc = ServiceRequestService(db_session)
    request = await _service_request_svc.create(
        ServiceRequestCreate.model_validate(
            {
                "requestNumber": generate_request_number(),
                "title": "Streetlight out",
                "description": "Dark corner",
                "category": RequestCategory.streetlight,
                "address": "3 Quay Road",
            }
        )
    )
    request.status = RequestStatus.assigned
    _service_request_svc = ServiceRequestService(db_session)
    request = await _service_request_svc.update(
        request.id, ServiceRequestUpdate(status=request.status)
    )
    assert event_spy.has(
        "RequestStatusChanged",
        request_id=request.id,
        request_number=request.request_number,
        old_status=RequestStatus.open,
        new_status=RequestStatus.assigned,
    )
