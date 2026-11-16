"""Specification tests for cityservices.GeocoderMock.

Auto-generated from DSL test blocks. Run with:
    pytest tests/spec/ -v -m spec
"""

from __future__ import annotations

import pytest

from cityservices_geocoder_mock.schemas.geocoder_db.known_address import (
    KnownAddressCreate,
)
from cityservices_geocoder_mock.services.geocoder_db.known_address_service import (
    KnownAddressService,
)


@pytest.mark.spec
async def test_a_known_address_keeps_its_lower_case_key(db_session):
    """a known address keeps its lower-case key"""
    _known_address_svc = KnownAddressService(db_session)
    known = await _known_address_svc.create(
        KnownAddressCreate.model_validate(
            {
                "address": "12 Harbor Street",
                "formattedAddress": "12 Harbor Street, Port Alder",
                "latitude": 47.6,
                "longitude": (-122.3),
            }
        )
    )
    assert known.address == "12 harbor street"
