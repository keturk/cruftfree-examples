"""NoticeDeskAPI route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_notice_service.auth import require_route
from helpdesk_notice_service.errors.problem_details import repeated_query_keys_guard
from helpdesk_notice_service.models.notice_db.notice import Notice
from helpdesk_notice_service.notice_db.session import get_notice_db_db
from helpdesk_notice_service.schemas.notice_db.notice import NoticeResponse
from helpdesk_notice_service.schemas.page import Page
from helpdesk_notice_service.schemas.page_request import PageRequest
from helpdesk_notice_service.services.notice_db.notice_service import NoticeService

router = APIRouter(
    prefix="/api/v1/desk/notices",
    tags=["NoticeDeskAPI"],
)


@router.get("", response_model=Page[NoticeResponse])
async def list_notices(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    recipient: Annotated[str | None, Query()] = None,
    delivered: Annotated[bool | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "recipient", "delivered"])
    ),
    notice_db: AsyncSession = Depends(get_notice_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["operator"],
            principal_types=["human"],
        )
    ),
) -> Page[Notice]:
    page = PageRequest(offset=skip, limit=limit)
    service = NoticeService(notice_db)
    return await service.get_all(page, recipient=recipient, delivered=delivered)
