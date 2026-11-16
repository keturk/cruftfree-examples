"""EmailAPI route handlers."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Security
from fastapi import status as http_status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_email_mock.auth import require_route
from helpdesk_email_mock.constants import BOUNCING_DOMAIN
from helpdesk_email_mock.email_db.session import get_email_db_db
from helpdesk_email_mock.enums.delivery_status import DeliveryStatus
from helpdesk_email_mock.models.email_db.outbound import Outbound
from helpdesk_email_mock.schemas.delivery import Delivery
from helpdesk_email_mock.schemas.email_db.outbound import OutboundCreate
from helpdesk_email_mock.schemas.send_email_request import SendEmailRequest
from helpdesk_email_mock.services.email_db.outbound_service import OutboundService

router = APIRouter(
    prefix="/v1",
    tags=["EmailAPI"],
)

# OpenAPI apiKey security schemes, one per API-key provider a route below
# admits. They only document the requirement: the API-key credential
# middleware has already authenticated a presented key before any route runs.
_api_key_scheme_email_keys = APIKeyHeader(
    name="X-Email-Api-Key", scheme_name="emailKeys", auto_error=False
)


@router.post(
    "/deliveries",
    response_model=Delivery,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Security(_api_key_scheme_email_keys)],
)
async def post_deliveries(
    *,
    request: Annotated[SendEmailRequest, Body()],
    email_db: AsyncSession = Depends(get_email_db_db),
    current_user=Depends(
        require_route(providers=["emailKeys"], roles=[], principal_types=["human"])
    ),
) -> Delivery:
    existing: Outbound | None = (
        (
            await email_db.execute(
                select(Outbound).where(
                    Outbound.idempotency_key == request.idempotency_key
                )
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        return Delivery(id=existing.delivery_id, status=existing.status)
    _outbound_svc = OutboundService(email_db)
    created = await _outbound_svc.create(
        OutboundCreate.model_validate(
            {
                "deliveryId": f"mail_{''.join(map(secrets.choice, ['0123456789abcdef'] * 24))}",
                "idempotencyKey": request.idempotency_key,
                "recipient": request.to,
                "subject": request.subject,
                "body": request.body,
                "status": (
                    DeliveryStatus.bounced
                    if request.to.endswith(BOUNCING_DOMAIN)
                    else DeliveryStatus.delivered
                ),
            }
        )
    )
    return Delivery(id=created.delivery_id, status=created.status)
