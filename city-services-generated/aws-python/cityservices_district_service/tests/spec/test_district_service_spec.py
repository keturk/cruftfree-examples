"""Specification tests for cityservices.DistrictService.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from cityservices_district_service.schemas.district_db.district import DistrictCreate
from cityservices_district_service.services.district_db.district_service import (
    DistrictService,
)


@pytest.mark.spec
async def test_a_new_district_starts_with_no_converted_boundary(db_session):
    """a new district starts with no converted boundary"""
    _district_svc = DistrictService(db_session)
    district = await _district_svc.create(
        DistrictCreate.model_validate(
            {
                "name": "Harborside",
                "code": "HBR",
                "boundaryGeoJson": '{"type":"Polygon","coordinates":[[[0,0],[0,1],[1,1],[1,0],[0,0]]]}',
            }
        )
    )
    assert district.boundary is None
