"""TicketAPI route handlers."""

import datetime
import secrets
import uuid
from enum import Enum as PyEnum
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi import status as http_status
from pydantic import BeforeValidator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_ticket_service._domain_formats import _cruftfree_require_uuid_text
from helpdesk_ticket_service.auth import require_route
from helpdesk_ticket_service.enums.priority import Priority
from helpdesk_ticket_service.enums.ticket_status import TicketStatus
from helpdesk_ticket_service.errors.domain_errors import (
    BadScoreError,
    ClosedTicketError,
    NotResolvedError,
)
from helpdesk_ticket_service.errors.problem_details import register_path_field_names
from helpdesk_ticket_service.event_outbox import (
    buffer_events as _cruftfree_buffer_events,
)
from helpdesk_ticket_service.functions import card_of, cards_of, own_ticket
from helpdesk_ticket_service.models.ticket_db.response_policy import ResponsePolicy
from helpdesk_ticket_service.models.ticket_db.ticket import Ticket
from helpdesk_ticket_service.models.ticket_db.ticket_message import TicketMessage
from helpdesk_ticket_service.mq import producer as _mq_producer
from helpdesk_ticket_service.schemas.customer_message import CustomerMessage
from helpdesk_ticket_service.schemas.customer_thread import CustomerThread
from helpdesk_ticket_service.schemas.open_ticket_request import OpenTicketRequest
from helpdesk_ticket_service.schemas.rate_request import RateRequest
from helpdesk_ticket_service.schemas.thread_entry import ThreadEntry
from helpdesk_ticket_service.schemas.ticket_card import TicketCard
from helpdesk_ticket_service.schemas.ticket_db.ticket import TicketCreate, TicketUpdate
from helpdesk_ticket_service.schemas.ticket_db.ticket_message import TicketMessageCreate
from helpdesk_ticket_service.services.ticket_db.ticket_message_service import (
    TicketMessageService,
)
from helpdesk_ticket_service.services.ticket_db.ticket_service import TicketService
from helpdesk_ticket_service.ticket_db.session import get_ticket_db_db

router = APIRouter(
    prefix="/api/v1/tickets",
    tags=["TicketAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "id": "id",
    }
)


@router.get("")
async def get_endpoint(
    *,
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"], roles=[], principal_types=["human"]
        )
    ),
) -> list[TicketCard]:
    return cards_of(
        list(
            (
                await ticket_db.execute(
                    select(Ticket)
                    .where(Ticket.customer_id == current_user.profile_id)
                    .order_by(Ticket.created_at.desc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
    )


@router.post("", response_model=TicketCard, status_code=http_status.HTTP_201_CREATED)
async def post_endpoint(
    *,
    request: Annotated[OpenTicketRequest, Body()],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"], roles=[], principal_types=["human"]
        )
    ),
) -> TicketCard:
    policy = (
        (
            await ticket_db.execute(
                select(ResponsePolicy).where(ResponsePolicy.priority == Priority.normal)
            )
        )
        .scalars()
        .first()
    )
    if policy is None:
        raise HTTPException(status_code=404, detail="Not found")
    customer_name: str = (
        [
            _operand
            for _operand in (current_user.identity.get("fullName"),)
            if _operand is not None
        ]
        or [
            (
                lambda _operand: (
                    _operand.value if isinstance(_operand, PyEnum) else str(_operand)
                )
            )(current_user.identity.get("email"))
        ]
    )[0]
    _ticket_svc = TicketService(ticket_db)
    ticket = await _ticket_svc.create(
        TicketCreate.model_validate(
            {
                "number": f"LP-{''.join(map(secrets.choice, ['0123456789'] * 6))}",
                "subject": request.subject,
                "topic": request.topic,
                "customerId": current_user.profile_id,
                "customerName": customer_name,
                "customerEmail": current_user.identity.get("email"),
                "respondBy": (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(minutes=policy.minutes)
                ),
            }
        )
    )
    _ticket_message_svc = TicketMessageService(ticket_db)
    _entity = await _ticket_message_svc.create(
        TicketMessageCreate.model_validate(
            {
                "ticketId": ticket.id,
                "authorName": customer_name,
                "fromCustomer": True,
                "body": request.body,
            }
        )
    )
    async with _cruftfree_buffer_events():
        _producer_instance = await _mq_producer.get_producer()
        await _producer_instance.publish_ticket_opened(
            ticket.number, ticket.subject, customer_name, str(ticket.customer_email)
        )
    return card_of(ticket)


# Answering a ticket that has gone quiet brings it back to an agent.
@router.post(
    "/reply", response_model=TicketCard, status_code=http_status.HTTP_201_CREATED
)
async def post_reply(
    *,
    request: Annotated[ThreadEntry, Body()],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"], roles=[], principal_types=["human"]
        )
    ),
) -> TicketCard:
    ticket: Ticket = await own_ticket(request.ticket_id, ticket_db, _commit=True)
    if ticket.status == TicketStatus.closed:
        raise ClosedTicketError()
    _ticket_message_svc = TicketMessageService(ticket_db)
    _entity = await _ticket_message_svc.create(
        TicketMessageCreate.model_validate(
            {
                "ticketId": ticket.id,
                "authorName": ticket.customer_name,
                "fromCustomer": True,
                "body": request.body,
            }
        )
    )
    ticket.status = TicketStatus.open
    ticket.resolved_at = None
    _ticket_svc = TicketService(ticket_db)
    ticket = await _ticket_svc.update(
        ticket.id, TicketUpdate(resolvedAt=ticket.resolved_at, status=ticket.status)
    )
    return card_of(ticket)


@router.post(
    "/{id}/rate", response_model=TicketCard, status_code=http_status.HTTP_201_CREATED
)
async def post_by_id_rate(
    *,
    request: Annotated[RateRequest, Body()],
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"], roles=[], principal_types=["human"]
        )
    ),
) -> TicketCard:
    if (request.score < 1) or (request.score > 5):
        raise BadScoreError()
    ticket: Ticket = await own_ticket(id_, ticket_db, _commit=True)
    if (ticket.status != TicketStatus.resolved) and (
        ticket.status != TicketStatus.closed
    ):
        raise NotResolvedError()
    ticket.satisfaction = request.score
    _ticket_svc = TicketService(ticket_db)
    ticket = await _ticket_svc.update(
        ticket.id, TicketUpdate(satisfaction=ticket.satisfaction)
    )
    return card_of(ticket)


@router.get("/{id}", response_model=CustomerThread)
async def get_by_id(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"], roles=[], principal_types=["human"]
        )
    ),
) -> CustomerThread:
    ticket: Ticket = await own_ticket(id_, ticket_db, _commit=True)
    said: list[TicketMessage] = list(
        (
            await ticket_db.execute(
                select(TicketMessage)
                .where(
                    TicketMessage.ticket_id == ticket.id,
                    TicketMessage.internal == False,
                )
                .order_by(TicketMessage.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    messages: list[CustomerMessage] = []
    for message in said:
        messages.append(
            CustomerMessage(
                authorName=message.author_name,
                fromCustomer=message.from_customer,
                body=message.body,
                createdAt=message.created_at,
            )
        )
    return CustomerThread(ticket=card_of(ticket), messages=messages)
