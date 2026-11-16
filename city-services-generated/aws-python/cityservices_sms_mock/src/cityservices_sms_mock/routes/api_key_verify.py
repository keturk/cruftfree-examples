"""_api_key_verify route handlers."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_sms_mock.api_key_verification import (
    ApiKeyVerifyResponse,
    answer_api_key_verification,
)
from cityservices_sms_mock.auth import require_route
from cityservices_sms_mock.schemas.api_key_verify_request import _ApiKeyVerifyRequest
from cityservices_sms_mock.sms_db.session import get_sms_db_db

router = APIRouter(
    prefix="/internal/identity/api-keys",
    tags=["_api_key_verify"],
)


@router.post(
    "/smsKeys/verify",
    response_model=ApiKeyVerifyResponse,
    status_code=http_status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_sms_keys_verify(
    *,
    request: Annotated[_ApiKeyVerifyRequest, Body()],
    sms_db: AsyncSession = Depends(get_sms_db_db),
    current_user=Depends(
        require_route(providers=["machine"], roles=[], principal_types=["machine"])
    ),
) -> ApiKeyVerifyResponse:
    return await answer_api_key_verification(sms_db, "smsKeys", request.key_hash)
