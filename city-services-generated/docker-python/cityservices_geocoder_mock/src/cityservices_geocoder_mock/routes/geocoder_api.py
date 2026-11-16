"""GeocoderAPI route handlers."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Security
from fastapi import status as http_status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_geocoder_mock._cruftfree_helpers import text_trim
from cityservices_geocoder_mock.auth import require_route
from cityservices_geocoder_mock.geocoder_db.session import get_geocoder_db_db
from cityservices_geocoder_mock.models.geocoder_db.known_address import KnownAddress
from cityservices_geocoder_mock.schemas.geocode_request import GeocodeRequest
from cityservices_geocoder_mock.schemas.geocode_result import GeocodeResult
from cityservices_geocoder_mock.schemas.geocoder_db.lookup import LookupCreate
from cityservices_geocoder_mock.services.geocoder_db.lookup_service import LookupService

router = APIRouter(
    prefix="/v1",
    tags=["GeocoderAPI"],
)

# OpenAPI apiKey security schemes, one per API-key provider a route below
# admits. They only document the requirement: the API-key credential
# middleware has already authenticated a presented key before any route runs.
_api_key_scheme_geocoder_keys = APIKeyHeader(
    name="X-Geocoder-Api-Key", scheme_name="geocoderKeys", auto_error=False
)


@router.post(
    "/geocode",
    response_model=GeocodeResult,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Security(_api_key_scheme_geocoder_keys)],
)
async def post_geocode(
    *,
    request: Annotated[GeocodeRequest, Body()],
    geocoder_db: AsyncSession = Depends(get_geocoder_db_db),
    current_user=Depends(
        require_route(
            providers=["geocoderKeys", "test_auth"], roles=[], principal_types=["human"]
        )
    ),
) -> GeocodeResult:
    known: KnownAddress | None = (
        (
            await geocoder_db.execute(
                select(KnownAddress).where(
                    KnownAddress.address == text_trim(request.query).lower()
                )
            )
        )
        .scalars()
        .first()
    )
    _lookup_svc = LookupService(geocoder_db)
    _entity = await _lookup_svc.create(
        LookupCreate.model_validate(
            {"query": request.query, "matched": (known is not None)}
        )
    )
    if known is None:
        return GeocodeResult(matched=False)
    return GeocodeResult(
        matched=True,
        latitude=known.latitude,
        longitude=known.longitude,
        formattedAddress=known.formatted_address,
    )
