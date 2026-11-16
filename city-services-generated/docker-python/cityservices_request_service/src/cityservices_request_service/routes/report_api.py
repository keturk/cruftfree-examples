"""ReportAPI route handlers."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from geoalchemy2 import Geography
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_request_service.enums.request_status import RequestStatus
from cityservices_request_service.errors.problem_details import (
    register_path_field_names,
    repeated_query_keys_guard,
)
from cityservices_request_service.functions import (
    generate_request_number,
    place,
    text_reporter,
    view_of,
)
from cityservices_request_service.models.request_db.service_request import (
    ServiceRequest,
)
from cityservices_request_service.request_db.session import get_request_db_db
from cityservices_request_service.schemas.report_request import ReportRequest
from cityservices_request_service.schemas.request_db.request_update import (
    RequestUpdateCreate,
)
from cityservices_request_service.schemas.request_db.service_request import (
    ServiceRequestCreate,
)
from cityservices_request_service.schemas.request_view import RequestView
from cityservices_request_service.services.request_db.request_update_service import (
    RequestUpdateService,
)
from cityservices_request_service.services.request_db.service_request_service import (
    ServiceRequestService,
)

router = APIRouter(
    prefix="/api/v1/reports",
    tags=["ReportAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "request_number": "requestNumber",
    }
)


@router.post("", response_model=RequestView, status_code=http_status.HTTP_201_CREATED)
async def post_endpoint(
    *,
    request: Annotated[ReportRequest, Body()],
    request_db: AsyncSession = Depends(get_request_db_db),
) -> RequestView:
    _service_request_svc = ServiceRequestService(request_db)
    created = await _service_request_svc.create(
        ServiceRequestCreate.model_validate(
            {
                "requestNumber": generate_request_number(),
                "title": request.title,
                "description": request.description,
                "category": request.category,
                "address": request.address,
                "reporterPhone": request.phone,
            }
        )
    )
    _request_update_svc = RequestUpdateService(request_db)
    _entity = await _request_update_svc.create(
        RequestUpdateCreate.model_validate(
            {
                "requestId": created.id,
                "status": RequestStatus.open,
                "note": "Report received",
            }
        )
    )
    await place(created, request_db, _commit=True)
    if request.phone is not None:
        await text_reporter(
            request.phone,
            f"receipt-{created.id}",
            f"Port Alder 311: we have your report. Your reference is {created.request_number}.",
        )
    return view_of(created)


# Open problems near a point: GeoSql lowers to ST_DWithin and ST_Distance.
@router.get("/nearby")
async def get_nearby(
    *,
    latitude: Annotated[float, Query()],
    longitude: Annotated[float, Query()],
    radius_meters: Annotated[float, Query(alias="radiusMeters")],
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["latitude", "longitude", "radiusMeters"])
    ),
    request_db: AsyncSession = Depends(get_request_db_db),
) -> list[RequestView]:
    near: list[ServiceRequest] = list(
        (
            await request_db.execute(
                select(ServiceRequest)
                .where(ServiceRequest.status == RequestStatus.open)
                .where(
                    func.ST_DWithin(
                        ServiceRequest.location.cast(Geography),
                        func.ST_SetSRID(
                            func.ST_MakePoint(longitude, latitude), 4326
                        ).cast(Geography),
                        radius_meters,
                    )
                )
                .order_by(
                    func.ST_Distance(
                        ServiceRequest.location.cast(Geography),
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
    return [view_of(r) for r in near]


@router.get("/track/{request_number}", response_model=RequestView)
async def get_track_by_request_number(
    *,
    request_number: Annotated[str, Path()],
    request_db: AsyncSession = Depends(get_request_db_db),
) -> RequestView:
    found = (
        (
            await request_db.execute(
                select(ServiceRequest).where(
                    ServiceRequest.request_number == request_number
                )
            )
        )
        .scalars()
        .first()
    )
    if found is None:
        raise HTTPException(status_code=404, detail="Not found")
    return view_of(found)
