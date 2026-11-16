"""FacilityAPI route handlers."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from geoalchemy2 import Geography
from pydantic import BeforeValidator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_facility_service._domain_formats import _cruftfree_require_uuid_text
from cityservices_facility_service.auth import require_route
from cityservices_facility_service.enums.facility_type import FacilityType
from cityservices_facility_service.errors.problem_details import (
    register_path_field_names,
    repeated_query_keys_guard,
)
from cityservices_facility_service.facility_db.session import get_facility_db_db
from cityservices_facility_service.functions import pin_of
from cityservices_facility_service.models.facility_db.facility import Facility
from cityservices_facility_service.models.facility_db.park import Park
from cityservices_facility_service.schemas.facility_db.facility import (
    FacilityResponse,
    FacilityUpdate,
)
from cityservices_facility_service.schemas.facility_db.park import ParkResponse
from cityservices_facility_service.schemas.facility_pin import FacilityPin
from cityservices_facility_service.schemas.page import Page
from cityservices_facility_service.schemas.page_request import PageRequest
from cityservices_facility_service.schemas.set_operational_request import (
    SetOperationalRequest,
)
from cityservices_facility_service.services.facility_db.facility_service import (
    FacilityService,
)

router = APIRouter(
    prefix="/api/v1/facilities",
    tags=["FacilityAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "id": "id",
    }
)


@router.get("", response_model=Page[FacilityResponse])
async def list_facilities(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    name: Annotated[str | None, Query()] = None,
    type_: Annotated[FacilityType | None, Query(alias="type")] = None,
    is_operational: Annotated[bool | None, Query(alias="isOperational")] = None,
    sort_by: Annotated[Literal["name"] | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[
        Literal["asc", "desc"] | None, Query(alias="sortOrder")
    ] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(
            ["skip", "limit", "name", "type", "isOperational", "sortBy", "sortOrder"]
        )
    ),
    facility_db: AsyncSession = Depends(get_facility_db_db),
) -> Page[Facility]:
    page = PageRequest(offset=skip, limit=limit)
    service = FacilityService(facility_db)
    return await service.get_all(
        page,
        sort_by=sort_by,
        sort_order=sort_order,
        name=name,
        type_=type_,
        is_operational=is_operational,
    )


@router.get("/map")
async def get_map(
    *,
    facility_db: AsyncSession = Depends(get_facility_db_db),
) -> list[FacilityPin]:
    open_: list[Facility] = list(
        (
            await facility_db.execute(
                select(Facility)
                .where(Facility.is_operational == True)
                .order_by(Facility.name.asc())
            )
        )
        .scalars()
        .all()
    )
    return [pin_of(f) for f in open_]


# GeoSql.withinDistanceMeters lowers to ST_DWithin and distanceMeters to ST_Distance.
@router.get("/nearby", response_model=list[FacilityResponse])
async def get_nearby(
    *,
    latitude: Annotated[float, Query()],
    longitude: Annotated[float, Query()],
    radius_meters: Annotated[float, Query(alias="radiusMeters")],
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["latitude", "longitude", "radiusMeters"])
    ),
    facility_db: AsyncSession = Depends(get_facility_db_db),
) -> list[Facility]:
    return list(
        (
            await facility_db.execute(
                select(Facility)
                .where(Facility.is_operational == True)
                .where(
                    func.ST_DWithin(
                        Facility.location.cast(Geography),
                        func.ST_SetSRID(
                            func.ST_MakePoint(longitude, latitude), 4326
                        ).cast(Geography),
                        radius_meters,
                    )
                )
                .order_by(
                    func.ST_Distance(
                        Facility.location.cast(Geography),
                        func.ST_SetSRID(
                            func.ST_MakePoint(longitude, latitude), 4326
                        ).cast(Geography),
                    )
                )
            )
        )
        .scalars()
        .all()
    )


@router.get("/parks", response_model=list[ParkResponse])
async def parks(
    *,
    facility_db: AsyncSession = Depends(get_facility_db_db),
) -> list[Park]:
    return list(
        (
            await facility_db.execute(
                select(Park).where(Park.is_open == True).order_by(Park.name.asc())
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/{id}/operational",
    response_model=FacilityResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_by_id_operational(
    *,
    request: Annotated[SetOperationalRequest, Body()],
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    facility_db: AsyncSession = Depends(get_facility_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"], roles=["admin"], principal_types=["human"]
        )
    ),
) -> Facility:
    service = FacilityService(facility_db)
    facility = await service.get(id_)
    if facility is None:
        raise HTTPException(status_code=404, detail="Not found")
    facility.is_operational = request.is_operational
    _facility_svc = FacilityService(facility_db)
    facility = await _facility_svc.update(
        facility.id, FacilityUpdate(isOperational=facility.is_operational)
    )
    return facility
