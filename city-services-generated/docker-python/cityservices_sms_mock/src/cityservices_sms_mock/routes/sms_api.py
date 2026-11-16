"""SmsAPI route handlers."""

import secrets
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Security
from fastapi import status as http_status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cityservices_sms_mock.auth import require_route
from cityservices_sms_mock.constants import FAILING_PREFIX
from cityservices_sms_mock.enums.text_status import TextStatus
from cityservices_sms_mock.models.sms_db.sent_sms import SentSms
from cityservices_sms_mock.schemas.send_sms_request import SendSmsRequest
from cityservices_sms_mock.schemas.sms_db.sent_sms import SentSmsCreate
from cityservices_sms_mock.schemas.text_message import TextMessage
from cityservices_sms_mock.services.sms_db.sent_sms_service import SentSmsService
from cityservices_sms_mock.sms_db.session import get_sms_db_db

router = APIRouter(
    prefix="/v1",
    tags=["SmsAPI"],
)

# OpenAPI apiKey security schemes, one per API-key provider a route below
# admits. They only document the requirement: the API-key credential
# middleware has already authenticated a presented key before any route runs.
_api_key_scheme_sms_keys = APIKeyHeader(
    name="X-Sms-Api-Key", scheme_name="smsKeys", auto_error=False
)


@router.post(
    "/messages",
    response_model=TextMessage,
    status_code=http_status.HTTP_201_CREATED,
    dependencies=[Security(_api_key_scheme_sms_keys)],
)
async def post_messages(
    *,
    request: Annotated[SendSmsRequest, Body()],
    sms_db: AsyncSession = Depends(get_sms_db_db),
    current_user=Depends(
        require_route(
            providers=["smsKeys", "test_auth"], roles=[], principal_types=["human"]
        )
    ),
) -> TextMessage:
    existing: SentSms | None = (
        (
            await sms_db.execute(
                select(SentSms).where(
                    SentSms.idempotency_key == request.idempotency_key
                )
            )
        )
        .scalars()
        .first()
    )
    if existing is not None:
        return TextMessage(id=existing.message_id, status=existing.status)
    _sent_sms_svc = SentSmsService(sms_db)
    created = await _sent_sms_svc.create(
        SentSmsCreate.model_validate(
            {
                "messageId": f"sms_{''.join(map(secrets.choice, ['0123456789abcdef'] * 24))}",
                "idempotencyKey": request.idempotency_key,
                "recipient": request.to,
                "body": request.body,
                "status": (
                    TextStatus.failed
                    if str(request.to).startswith(FAILING_PREFIX)
                    else TextStatus.delivered
                ),
            }
        )
    )
    return TextMessage(id=created.message_id, status=created.status)
