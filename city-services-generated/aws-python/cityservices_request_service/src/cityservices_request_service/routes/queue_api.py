"""QueueAPI route handlers."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from pydantic import BeforeValidator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_request_service._domain_formats import _cruftfree_require_uuid_text
from cityservices_request_service.auth import require_route
from cityservices_request_service.enums.request_category import RequestCategory
from cityservices_request_service.enums.request_priority import RequestPriority
from cityservices_request_service.enums.request_status import RequestStatus
from cityservices_request_service.errors.problem_details import (
    register_path_field_names,
    repeated_query_keys_guard,
)
from cityservices_request_service.functions import advance, pin_of
from cityservices_request_service.models.request_db.request_update import RequestUpdate
from cityservices_request_service.models.request_db.service_request import (
    ServiceRequest,
)
from cityservices_request_service.request_db.session import get_request_db_db
from cityservices_request_service.schemas.page import Page
from cityservices_request_service.schemas.page_request import PageRequest
from cityservices_request_service.schemas.queue_summary import QueueSummary
from cityservices_request_service.schemas.request_db.request_update import (
    RequestUpdateResponse,
)
from cityservices_request_service.schemas.request_db.service_request import (
    ServiceRequestResponse,
    ServiceRequestUpdate,
)
from cityservices_request_service.schemas.request_pin import RequestPin
from cityservices_request_service.schemas.set_priority_request import SetPriorityRequest
from cityservices_request_service.services.request_db.service_request_service import (
    ServiceRequestService,
)

router = APIRouter(
    prefix="/api/v1/queue/requests",
    tags=["QueueAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "id": "id",
    }
)


@router.get("/service_requests", response_model=Page[ServiceRequestResponse])
async def list_service_requests(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    request_number: Annotated[str | None, Query(alias="requestNumber")] = None,
    title: Annotated[str | None, Query()] = None,
    category: Annotated[RequestCategory | None, Query()] = None,
    priority: Annotated[RequestPriority | None, Query()] = None,
    status: Annotated[RequestStatus | None, Query()] = None,
    district_name: Annotated[str | None, Query(alias="districtName")] = None,
    sort_by: Annotated[Literal["priority"] | None, Query(alias="sortBy")] = None,
    sort_order: Annotated[
        Literal["asc", "desc"] | None, Query(alias="sortOrder")
    ] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(
            [
                "skip",
                "limit",
                "requestNumber",
                "title",
                "category",
                "priority",
                "status",
                "districtName",
                "sortBy",
                "sortOrder",
            ]
        )
    ),
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> Page[ServiceRequest]:
    page = PageRequest(offset=skip, limit=limit)
    service = ServiceRequestService(request_db)
    return await service.get_all(
        page,
        sort_by=sort_by,
        sort_order=sort_order,
        request_number=request_number,
        title=title,
        category=category,
        priority=priority,
        status=status,
        district_name=district_name,
    )


@router.get("/summary", response_model=QueueSummary)
async def get_summary(
    *,
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> QueueSummary:
    return QueueSummary(
        open=(
            (
                await request_db.execute(
                    select(func.count()).select_from(
                        (
                            select(ServiceRequest).where(
                                ServiceRequest.status == RequestStatus.open
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
        assigned=(
            (
                await request_db.execute(
                    select(func.count()).select_from(
                        (
                            select(ServiceRequest).where(
                                ServiceRequest.status == RequestStatus.assigned
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
        inProgress=(
            (
                await request_db.execute(
                    select(func.count()).select_from(
                        (
                            select(ServiceRequest).where(
                                ServiceRequest.status == RequestStatus.in_progress
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
        needsLocation=(
            (
                await request_db.execute(
                    select(func.count()).select_from(
                        (
                            select(ServiceRequest).where(
                                ServiceRequest.latitude == None
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
    )


@router.get("/map")
async def get_map(
    *,
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> list[RequestPin]:
    open_: list[ServiceRequest] = list(
        (
            await request_db.execute(
                select(ServiceRequest).where(
                    ServiceRequest.status == RequestStatus.open
                )
            )
        )
        .scalars()
        .all()
    )
    return [pin_of(r) for r in [x for x in open_ if (x.latitude is not None)]]


@router.post(
    "/{id}/priority",
    response_model=ServiceRequestResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_by_id_priority(
    *,
    request: Annotated[SetPriorityRequest, Body()],
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> ServiceRequest:
    service = ServiceRequestService(request_db)
    found = await service.get(id_)
    if found is None:
        raise HTTPException(status_code=404, detail="Not found")
    found.priority = request.priority
    _service_request_svc = ServiceRequestService(request_db)
    found = await _service_request_svc.update(
        found.id, ServiceRequestUpdate(priority=found.priority)
    )
    return found


@router.get("/{id}/history", response_model=list[RequestUpdateResponse])
async def get_by_id_history(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> list[RequestUpdate]:
    return list(
        (
            await request_db.execute(
                select(RequestUpdate)
                .where(RequestUpdate.request_id == id_)
                .order_by(RequestUpdate.created_at.asc())
            )
        )
        .scalars()
        .all()
    )


@router.post(
    "/{id}/resolve",
    response_model=ServiceRequestResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_by_id_resolve(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> ServiceRequest:
    service = ServiceRequestService(request_db)
    found = await service.get(id_)
    if found is None:
        raise HTTPException(status_code=404, detail="Not found")
    await advance(
        found,
        RequestStatus.in_progress,
        RequestStatus.resolved,
        "Marked resolved",
        request_db,
        _commit=True,
    )
    return found


@router.post(
    "/{id}/assign",
    response_model=ServiceRequestResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_by_id_assign(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> ServiceRequest:
    service = ServiceRequestService(request_db)
    found = await service.get(id_)
    if found is None:
        raise HTTPException(status_code=404, detail="Not found")
    await advance(
        found,
        RequestStatus.open,
        RequestStatus.assigned,
        "Assigned to a crew",
        request_db,
        _commit=True,
    )
    return found


@router.post(
    "/{id}/close",
    response_model=ServiceRequestResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_by_id_close(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> ServiceRequest:
    service = ServiceRequestService(request_db)
    found = await service.get(id_)
    if found is None:
        raise HTTPException(status_code=404, detail="Not found")
    await advance(
        found,
        RequestStatus.resolved,
        RequestStatus.closed,
        "Closed",
        request_db,
        _commit=True,
    )
    return found


@router.post(
    "/{id}/start",
    response_model=ServiceRequestResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_by_id_start(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> ServiceRequest:
    service = ServiceRequestService(request_db)
    found = await service.get(id_)
    if found is None:
        raise HTTPException(status_code=404, detail="Not found")
    await advance(
        found,
        RequestStatus.assigned,
        RequestStatus.in_progress,
        "Work started",
        request_db,
        _commit=True,
    )
    return found


@router.get("/{id}", response_model=ServiceRequestResponse)
async def get_by_id(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    request_db: AsyncSession = Depends(get_request_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"],
            roles=["dispatcher", "admin"],
            principal_types=["human"],
        )
    ),
) -> ServiceRequest:
    service = ServiceRequestService(request_db)
    return await service.get(id_)
