"""_api_key_verify route handlers."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi import status as http_status
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_email_mock.api_key_verification import (
    ApiKeyVerifyResponse,
    answer_api_key_verification,
)
from helpdesk_email_mock.auth import require_route
from helpdesk_email_mock.email_db.session import get_email_db_db
from helpdesk_email_mock.schemas.api_key_verify_request import _ApiKeyVerifyRequest

router = APIRouter(
    prefix="/internal/identity/api-keys",
    tags=["_api_key_verify"],
)


@router.post(
    "/emailKeys/verify",
    response_model=ApiKeyVerifyResponse,
    status_code=http_status.HTTP_201_CREATED,
    include_in_schema=False,
)
async def post_email_keys_verify(
    *,
    request: Annotated[_ApiKeyVerifyRequest, Body()],
    email_db: AsyncSession = Depends(get_email_db_db),
    current_user=Depends(
        require_route(
            providers=["machine", "test_auth"], roles=[], principal_types=["machine"]
        )
    ),
) -> ApiKeyVerifyResponse:
    return await answer_api_key_verification(email_db, "emailKeys", request.key_hash)
