"""_api_key_verify route handlers."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_geocoder_mock.api_key_verification import (
    ApiKeyVerifyResponse,
    answer_api_key_verification,
)
from cityservices_geocoder_mock.auth import require_route
from cityservices_geocoder_mock.geocoder_db.session import get_geocoder_db_db
from cityservices_geocoder_mock.schemas.api_key_verify_request import (
    _ApiKeyVerifyRequest,
)

router = APIRouter(
    prefix="/internal/identity/api-keys",
    tags=["_api_key_verify"],
)


@router.post(
    "/geocoderKeys/verify",
    response_model=ApiKeyVerifyResponse,
    status_code=http_status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_geocoder_keys_verify(
    *,
    request: Annotated[_ApiKeyVerifyRequest, Body()],
    geocoder_db: AsyncSession = Depends(get_geocoder_db_db),
    current_user=Depends(
        require_route(providers=["machine"], roles=[], principal_types=["machine"])
    ),
) -> ApiKeyVerifyResponse:
    return await answer_api_key_verification(
        geocoder_db, "geocoderKeys", request.key_hash
    )
