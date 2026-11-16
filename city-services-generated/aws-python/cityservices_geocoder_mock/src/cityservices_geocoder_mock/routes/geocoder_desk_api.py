"""GeocoderDeskAPI route handlers."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query
from fastapi import status as http_status
from pydantic import BeforeValidator
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_geocoder_mock._domain_formats import _cruftfree_require_uuid_text
from cityservices_geocoder_mock.auth import require_route
from cityservices_geocoder_mock.errors.problem_details import (
    register_path_field_names,
    repeated_query_keys_guard,
)
from cityservices_geocoder_mock.geocoder_db.session import get_geocoder_db_db
from cityservices_geocoder_mock.models.geocoder_db.known_address import KnownAddress
from cityservices_geocoder_mock.models.geocoder_db.lookup import Lookup
from cityservices_geocoder_mock.schemas.geocoder_db.known_address import (
    KnownAddressCreate,
    KnownAddressResponse,
)
from cityservices_geocoder_mock.schemas.geocoder_db.lookup import LookupResponse
from cityservices_geocoder_mock.schemas.page import Page
from cityservices_geocoder_mock.schemas.page_request import PageRequest
from cityservices_geocoder_mock.services.geocoder_db.known_address_service import (
    KnownAddressService,
)
from cityservices_geocoder_mock.services.geocoder_db.lookup_service import LookupService

router = APIRouter(
    prefix="/api/v1/desk/geocoder",
    tags=["GeocoderDeskAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "id": "id",
    }
)


@router.get("/lookups", response_model=Page[LookupResponse])
async def list_lookups(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    query: Annotated[str | None, Query()] = None,
    matched: Annotated[bool | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "query", "matched"])
    ),
    geocoder_db: AsyncSession = Depends(get_geocoder_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"], roles=["operator"], principal_types=["human"]
        )
    ),
) -> Page[Lookup]:
    page = PageRequest(offset=skip, limit=limit)
    service = LookupService(geocoder_db)
    return await service.get_all(page, query=query, matched=matched)


@router.get("/known_addresses", response_model=Page[KnownAddressResponse])
async def list_known_addresses(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    address: Annotated[str | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "address"])
    ),
    geocoder_db: AsyncSession = Depends(get_geocoder_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"], roles=["operator"], principal_types=["human"]
        )
    ),
) -> Page[KnownAddress]:
    page = PageRequest(offset=skip, limit=limit)
    service = KnownAddressService(geocoder_db)
    return await service.get_all(page, address=address)


@router.post(
    "/known_addresses",
    response_model=KnownAddressResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_known_address(
    *,
    body: Annotated[KnownAddressCreate, Body()],
    geocoder_db: AsyncSession = Depends(get_geocoder_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"], roles=["operator"], principal_types=["human"]
        )
    ),
) -> KnownAddress:
    service = KnownAddressService(geocoder_db)
    return await service.create(body)


@router.delete("/known_addresses/{id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_known_address(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    geocoder_db: AsyncSession = Depends(get_geocoder_db_db),
    current_user=Depends(
        require_route(
            providers=["identity"], roles=["operator"], principal_types=["human"]
        )
    ),
) -> None:
    service = KnownAddressService(geocoder_db)
    await service.delete(id_)
