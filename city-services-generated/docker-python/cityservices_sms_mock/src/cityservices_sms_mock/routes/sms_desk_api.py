"""SmsDeskAPI route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_sms_mock.auth import require_route
from cityservices_sms_mock.enums.text_status import TextStatus
from cityservices_sms_mock.errors.problem_details import repeated_query_keys_guard
from cityservices_sms_mock.models.sms_db.sent_sms import SentSms
from cityservices_sms_mock.schemas.page import Page
from cityservices_sms_mock.schemas.page_request import PageRequest
from cityservices_sms_mock.schemas.sms_db.sent_sms import SentSmsResponse
from cityservices_sms_mock.services.sms_db.sent_sms_service import SentSmsService
from cityservices_sms_mock.sms_db.session import get_sms_db_db

router = APIRouter(
    prefix="/api/v1/desk/sms",
    tags=["SmsDeskAPI"],
)


@router.get("/sent_sms", response_model=Page[SentSmsResponse])
async def list_sent_sms(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[TextStatus | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "status"])
    ),
    sms_db: AsyncSession = Depends(get_sms_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["operator"],
            principal_types=["human"],
        )
    ),
) -> Page[SentSms]:
    page = PageRequest(offset=skip, limit=limit)
    service = SentSmsService(sms_db)
    return await service.get_all(page, status=status)
