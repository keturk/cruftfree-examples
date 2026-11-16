"""EmailDeskAPI route handlers."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_email_mock.auth import require_route
from helpdesk_email_mock.email_db.session import get_email_db_db
from helpdesk_email_mock.enums.delivery_status import DeliveryStatus
from helpdesk_email_mock.errors.problem_details import repeated_query_keys_guard
from helpdesk_email_mock.models.email_db.outbound import Outbound
from helpdesk_email_mock.schemas.email_db.outbound import OutboundResponse
from helpdesk_email_mock.schemas.page import Page
from helpdesk_email_mock.schemas.page_request import PageRequest
from helpdesk_email_mock.services.email_db.outbound_service import OutboundService

router = APIRouter(
    prefix="/api/v1/desk/email",
    tags=["EmailDeskAPI"],
)


@router.get("/outbounds", response_model=Page[OutboundResponse])
async def list_outbounds(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    recipient: Annotated[str | None, Query()] = None,
    subject: Annotated[str | None, Query()] = None,
    status: Annotated[DeliveryStatus | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "recipient", "subject", "status"])
    ),
    email_db: AsyncSession = Depends(get_email_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["operator"],
            principal_types=["human"],
        )
    ),
) -> Page[Outbound]:
    page = PageRequest(offset=skip, limit=limit)
    service = OutboundService(email_db)
    return await service.get_all(
        page, recipient=recipient, subject=subject, status=status
    )
