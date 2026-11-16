"""Specification tests for cityservices.FacilityService.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from cityservices_facility_service.enums.facility_type import FacilityType
from cityservices_facility_service.schemas.facility_db.facility import FacilityCreate
from cityservices_facility_service.services.facility_db.facility_service import (
    FacilityService,
)


@pytest.mark.spec
async def test_a_new_facility_is_operational(db_session):
    """a new facility is operational"""
    _facility_svc = FacilityService(db_session)
    facility = await _facility_svc.create(
        FacilityCreate.model_validate(
            {
                "name": "Harborside Library",
                "type": FacilityType.library,
                "latitude": 47.6,
                "longitude": (-122.3),
                "address": "12 Harbor Street",
                "phone": "+14155550123",
            }
        )
    )
    assert facility.is_operational
