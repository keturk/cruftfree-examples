"""DistrictAPI route handlers."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_district_service.auth import require_route
from cityservices_district_service.district_db.session import get_district_db_db
from cityservices_district_service.errors.problem_details import (
    repeated_query_keys_guard,
)
from cityservices_district_service.functions import facts_of
from cityservices_district_service.models.district_db.district import District
from cityservices_district_service.models.district_db.zoning_area import ZoningArea
from cityservices_district_service.schemas.district_db.district import DistrictResponse
from cityservices_district_service.schemas.district_db.zoning_area import (
    ZoningAreaResponse,
)
from cityservices_district_service.schemas.district_facts import DistrictFacts
from cityservices_district_service.schemas.district_match import DistrictMatch
from cityservices_district_service.schemas.page import Page
from cityservices_district_service.schemas.page_request import PageRequest
from cityservices_district_service.services.district_db.district_service import (
    DistrictService,
)

router = APIRouter(
    prefix="/api/v1/districts",
    tags=["DistrictAPI"],
)


@router.get("", response_model=Page[DistrictResponse])
async def list_districts(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    name: Annotated[str | None, Query()] = None,
    sort_by: Annotated[Literal["name"] | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[
        Literal["asc", "desc"] | None, Query(alias="sortOrder")
    ] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "name", "sortBy", "sortOrder"])
    ),
    district_db: AsyncSession = Depends(get_district_db_db),
) -> Page[District]:
    page = PageRequest(offset=skip, limit=limit)
    service = DistrictService(district_db)
    return await service.get_all(
        page, sort_by=sort_by, sort_order=sort_order, name=name
    )


# GeoSql.containsPoint lowers to ST_Contains, answered by the spatial index.
@router.get("/for-location", response_model=DistrictMatch)
async def get_for_location(
    *,
    latitude: Annotated[float, Query()],
    longitude: Annotated[float, Query()],
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["latitude", "longitude"])
    ),
    district_db: AsyncSession = Depends(get_district_db_db),
    current_user=Depends(
        require_route(providers=["machine"], roles=[], principal_types=["machine"])
    ),
) -> DistrictMatch:
    district: District | None = (
        (
            await district_db.execute(
                select(District).where(
                    func.ST_Contains(
                        District.boundary,
                        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
                    )
                )
            )
        )
        .scalars()
        .first()
    )
    if district is None:
        return DistrictMatch(found=False)
    return DistrictMatch(found=True, districtId=district.id, name=district.name)


@router.get("/zoning", response_model=list[ZoningAreaResponse])
async def get_zoning(
    *,
    latitude: Annotated[float, Query()],
    longitude: Annotated[float, Query()],
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["latitude", "longitude"])
    ),
    district_db: AsyncSession = Depends(get_district_db_db),
) -> list[ZoningArea]:
    return list(
        (
            await district_db.execute(
                select(ZoningArea).where(
                    func.ST_Contains(
                        ZoningArea.boundary,
                        func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
                    )
                )
            )
        )
        .scalars()
        .all()
    )


@router.get("/facts")
async def get_facts(
    *,
    district_db: AsyncSession = Depends(get_district_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> list[DistrictFacts]:
    all_: list[District] = list(
        (await district_db.execute(select(District).order_by(District.name.asc())))
        .scalars()
        .all()
    )
    return [facts_of(d) for d in all_]
