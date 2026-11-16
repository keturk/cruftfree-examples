"""AgentAPI route handlers."""

import datetime
import uuid
from enum import Enum as PyEnum
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from fastapi import status as http_status
from pydantic import BeforeValidator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_ticket_service._cruftfree_helpers import _cruftfree_format_datetime
from helpdesk_ticket_service._domain_formats import _cruftfree_require_uuid_text
from helpdesk_ticket_service.auth import require_route
from helpdesk_ticket_service.enums.priority import Priority
from helpdesk_ticket_service.enums.ticket_status import TicketStatus
from helpdesk_ticket_service.enums.ticket_topic import TicketTopic
from helpdesk_ticket_service.errors.domain_errors import BadMoveError, ClosedTicketError
from helpdesk_ticket_service.errors.problem_details import (
    register_path_field_names,
    repeated_query_keys_guard,
)
from helpdesk_ticket_service.event_outbox import (
    buffer_events as _cruftfree_buffer_events,
)
from helpdesk_ticket_service.functions import card_of, cards_of, resolve
from helpdesk_ticket_service.models.ticket_db.saved_reply import SavedReply
from helpdesk_ticket_service.models.ticket_db.ticket import Ticket
from helpdesk_ticket_service.models.ticket_db.ticket_message import TicketMessage
from helpdesk_ticket_service.mq import producer as _mq_producer
from helpdesk_ticket_service.schemas.agent_message import AgentMessage
from helpdesk_ticket_service.schemas.agent_thread import AgentThread
from helpdesk_ticket_service.schemas.desk_summary import DeskSummary
from helpdesk_ticket_service.schemas.move_request import MoveRequest
from helpdesk_ticket_service.schemas.page import Page
from helpdesk_ticket_service.schemas.page_request import PageRequest
from helpdesk_ticket_service.schemas.thread_entry import ThreadEntry
from helpdesk_ticket_service.schemas.ticket_card import TicketCard
from helpdesk_ticket_service.schemas.ticket_db.saved_reply import (
    SavedReplyCreate,
    SavedReplyResponse,
    SavedReplyUpdate,
)
from helpdesk_ticket_service.schemas.ticket_db.ticket import (
    TicketResponse,
    TicketUpdate,
)
from helpdesk_ticket_service.schemas.ticket_db.ticket_message import TicketMessageCreate
from helpdesk_ticket_service.schemas.volume_point import VolumePoint
from helpdesk_ticket_service.services.ticket_db.saved_reply_service import (
    SavedReplyService,
)
from helpdesk_ticket_service.services.ticket_db.ticket_message_service import (
    TicketMessageService,
)
from helpdesk_ticket_service.services.ticket_db.ticket_service import TicketService
from helpdesk_ticket_service.ticket_db.session import get_ticket_db_db

router = APIRouter(
    prefix="/api/v1/agent",
    tags=["AgentAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "id": "id",
    }
)


@router.get("/tickets", response_model=Page[TicketResponse])
async def list_tickets(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    subject: Annotated[str | None, Query()] = None,
    topic: Annotated[TicketTopic | None, Query()] = None,
    priority: Annotated[Priority | None, Query()] = None,
    status: Annotated[TicketStatus | None, Query()] = None,
    customer_name: Annotated[str | None, Query(alias="customerName")] = None,
    assignee_name: Annotated[str | None, Query(alias="assigneeName")] = None,
    breached: Annotated[bool | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(
            [
                "skip",
                "limit",
                "subject",
                "topic",
                "priority",
                "status",
                "customerName",
                "assigneeName",
                "breached",
            ]
        )
    ),
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> Page[Ticket]:
    page = PageRequest(offset=skip, limit=limit)
    service = TicketService(ticket_db)
    return await service.get_all(
        page,
        subject=subject,
        topic=topic,
        priority=priority,
        status=status,
        customer_name=customer_name,
        assignee_name=assignee_name,
        breached=breached,
    )


@router.get("/saved_replies", response_model=Page[SavedReplyResponse])
async def list_saved_replies(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    title: Annotated[str | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "title"])
    ),
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> Page[SavedReply]:
    page = PageRequest(offset=skip, limit=limit)
    service = SavedReplyService(ticket_db)
    return await service.get_all(page, title=title)


@router.post(
    "/saved_replies",
    response_model=SavedReplyResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_saved_reply(
    *,
    body: Annotated[SavedReplyCreate, Body()],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> SavedReply:
    service = SavedReplyService(ticket_db)
    return await service.create(body)


# What the reply dialog offers, in the order a person finds them.
@router.get("/reply-choices", response_model=list[SavedReplyResponse])
async def get_reply_choices(
    *,
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> list[SavedReply]:
    return list(
        (
            await ticket_db.execute(
                select(SavedReply).order_by(SavedReply.title.asc()).limit(100)
            )
        )
        .scalars()
        .all()
    )


# Everything still moving, soonest clock first.
@router.get("/queue")
async def get_queue(
    *,
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> list[TicketCard]:
    return cards_of(
        list(
            (
                await ticket_db.execute(
                    select(Ticket)
                    .where(
                        Ticket.status.in_(
                            [
                                TicketStatus.new,
                                TicketStatus.open,
                                TicketStatus.waiting,
                                TicketStatus.resolved,
                            ]
                        )
                    )
                    .order_by(Ticket.respond_by.asc())
                    .limit(200)
                )
            )
            .scalars()
            .all()
        )
    )


@router.get("/mine")
async def get_mine(
    *,
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> list[TicketCard]:
    return cards_of(
        list(
            (
                await ticket_db.execute(
                    select(Ticket)
                    .where(Ticket.assignee_id == current_user.profile_id)
                    .where(
                        Ticket.status.in_(
                            [TicketStatus.new, TicketStatus.open, TicketStatus.waiting]
                        )
                    )
                    .order_by(Ticket.respond_by.asc())
                    .limit(100)
                )
            )
            .scalars()
            .all()
        )
    )


# A public answer stops the clock and waits for the customer.
@router.post(
    "/reply", response_model=TicketCard, status_code=http_status.HTTP_201_CREATED
)
async def post_reply(
    *,
    request: Annotated[ThreadEntry, Body()],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> TicketCard:
    service = TicketService(ticket_db)
    ticket = await service.get(request.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Not found")
    if ticket.status == TicketStatus.closed:
        raise ClosedTicketError()
    agent_name: str = (
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
    _ticket_message_svc = TicketMessageService(ticket_db)
    _entity = await _ticket_message_svc.create(
        TicketMessageCreate.model_validate(
            {"ticketId": ticket.id, "authorName": agent_name, "body": request.body}
        )
    )
    if ticket.first_replied_at is None:
        ticket.first_replied_at = datetime.datetime.now(datetime.timezone.utc)
    if ticket.assignee_id is None:
        ticket.assignee_id = current_user.profile_id
        ticket.assignee_name = agent_name
    ticket.status = TicketStatus.waiting
    _ticket_svc = TicketService(ticket_db)
    ticket = await _ticket_svc.update(
        ticket.id,
        TicketUpdate(
            assigneeId=ticket.assignee_id,
            assigneeName=ticket.assignee_name,
            firstRepliedAt=ticket.first_replied_at,
            status=ticket.status,
        ),
    )
    async with _cruftfree_buffer_events():
        _producer_instance = await _mq_producer.get_producer()
        await _producer_instance.publish_agent_replied(
            ticket.number,
            ticket.subject,
            agent_name,
            str(ticket.customer_email),
            request.body,
        )
    return card_of(ticket)


# A note is for colleagues. It stops no clock and tells no one.
@router.post(
    "/note", response_model=TicketCard, status_code=http_status.HTTP_201_CREATED
)
async def post_note(
    *,
    request: Annotated[ThreadEntry, Body()],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> TicketCard:
    service = TicketService(ticket_db)
    ticket = await service.get(request.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Not found")
    _ticket_message_svc = TicketMessageService(ticket_db)
    _entity = await _ticket_message_svc.create(
        TicketMessageCreate.model_validate(
            {
                "ticketId": ticket.id,
                "authorName": (
                    [
                        _operand
                        for _operand in (current_user.identity.get("fullName"),)
                        if _operand is not None
                    ]
                    or [
                        (
                            lambda _operand: (
                                _operand.value
                                if isinstance(_operand, PyEnum)
                                else str(_operand)
                            )
                        )(current_user.identity.get("email"))
                    ]
                )[0],
                "internal": True,
                "body": request.body,
            }
        )
    )
    return card_of(ticket)


@router.get("/summary", response_model=DeskSummary)
async def get_summary(
    *,
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> DeskSummary:
    scored: list[Ticket] = list(
        (
            await ticket_db.execute(
                select(Ticket).where(Ticket.satisfaction >= 1).limit(500)
            )
        )
        .scalars()
        .all()
    )
    total: int = 0
    count: int = 0
    for ticket in scored:
        total = total + (ticket.satisfaction if ticket.satisfaction is not None else 0)
        count = count + 1
    return DeskSummary(
        open=(
            (
                await ticket_db.execute(
                    select(func.count()).select_from(
                        (
                            select(Ticket).where(
                                Ticket.status.in_(
                                    [
                                        TicketStatus.new,
                                        TicketStatus.open,
                                        TicketStatus.waiting,
                                    ]
                                )
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
        unassigned=(
            (
                await ticket_db.execute(
                    select(func.count()).select_from(
                        (
                            select(Ticket)
                            .where(Ticket.assignee_id == None)
                            .where(
                                Ticket.status.in_([TicketStatus.new, TicketStatus.open])
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
        late=(
            (
                await ticket_db.execute(
                    select(func.count()).select_from(
                        (
                            select(Ticket)
                            .where(Ticket.breached == True)
                            .where(
                                Ticket.status.in_([TicketStatus.new, TicketStatus.open])
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
        resolvedToday=(
            (
                await ticket_db.execute(
                    select(func.count()).select_from(
                        (
                            select(Ticket).where(
                                Ticket.resolved_at
                                >= datetime.datetime.now(datetime.timezone.utc).replace(
                                    hour=0, minute=0, second=0, microsecond=0
                                )
                            )
                        ).subquery()
                    )
                )
            ).scalar()
            or 0
        ),
        averageScore=(0.0 if (count == 0) else (float(total) / float(count))),
    )


@router.get("/volume")
async def get_volume(
    *,
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> list[VolumePoint]:
    points: list[VolumePoint] = []
    for back in [13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]:
        start: datetime.datetime = datetime.datetime.now(datetime.timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + datetime.timedelta(days=(0 - back))
        points.append(
            VolumePoint(
                day=_cruftfree_format_datetime(start, "MMM dd"),
                opened=(
                    (
                        await ticket_db.execute(
                            select(func.count()).select_from(
                                (
                                    select(Ticket).where(
                                        Ticket.created_at >= start,
                                        Ticket.created_at
                                        < (start + datetime.timedelta(days=1)),
                                    )
                                ).subquery()
                            )
                        )
                    ).scalar()
                    or 0
                ),
            )
        )
    return points


@router.get("/saved_replies/{id}", response_model=SavedReplyResponse)
async def get_saved_reply(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> SavedReply:
    service = SavedReplyService(ticket_db)
    return await service.get(id_)


@router.put("/saved_replies/{id}", response_model=SavedReplyResponse)
async def update_saved_reply(
    *,
    body: Annotated[SavedReplyUpdate, Body()],
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> SavedReply:
    service = SavedReplyService(ticket_db)
    return await service.update(id_, body)


@router.delete("/saved_replies/{id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_saved_reply(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> None:
    service = SavedReplyService(ticket_db)
    await service.delete(id_)


@router.post(
    "/threads/{id}/claim",
    response_model=TicketCard,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_threads_by_id_claim(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> TicketCard:
    service = TicketService(ticket_db)
    ticket = await service.get(id_)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Not found")
    ticket.assignee_id = current_user.profile_id
    ticket.assignee_name = (
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
    if ticket.status == TicketStatus.new:
        ticket.status = TicketStatus.open
    _ticket_svc = TicketService(ticket_db)
    ticket = await _ticket_svc.update(
        ticket.id,
        TicketUpdate(
            assigneeId=ticket.assignee_id,
            assigneeName=ticket.assignee_name,
            status=ticket.status,
        ),
    )
    return card_of(ticket)


# The queue's columns. A ticket closes only after it was resolved.
@router.post(
    "/threads/{id}/move",
    response_model=TicketCard,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_threads_by_id_move(
    *,
    request: Annotated[MoveRequest, Body()],
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> TicketCard:
    service = TicketService(ticket_db)
    ticket = await service.get(id_)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Not found")
    if request.status == ticket.status:
        return card_of(ticket)
    if ticket.status == TicketStatus.closed:
        raise ClosedTicketError()
    if (request.status == TicketStatus.new) or (
        (request.status == TicketStatus.closed)
        and (ticket.status != TicketStatus.resolved)
    ):
        raise BadMoveError()
    if request.status == TicketStatus.resolved:
        await resolve(ticket, ticket_db, _commit=True)
        return card_of(ticket)
    ticket.status = request.status
    _ticket_svc = TicketService(ticket_db)
    ticket = await _ticket_svc.update(ticket.id, TicketUpdate(status=ticket.status))
    return card_of(ticket)


@router.get("/threads/{id}", response_model=AgentThread)
async def get_threads_by_id(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    ticket_db: AsyncSession = Depends(get_ticket_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> AgentThread:
    service = TicketService(ticket_db)
    ticket = await service.get(id_)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Not found")
    said: list[TicketMessage] = list(
        (
            await ticket_db.execute(
                select(TicketMessage)
                .where(TicketMessage.ticket_id == id_)
                .order_by(TicketMessage.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    messages: list[AgentMessage] = []
    for message in said:
        messages.append(
            AgentMessage(
                authorName=message.author_name,
                fromCustomer=message.from_customer,
                internal=message.internal,
                body=message.body,
                createdAt=message.created_at,
            )
        )
    return AgentThread(
        ticket=card_of(ticket),
        customerEmail=str(ticket.customer_email),
        mine=(ticket.assignee_id == current_user.profile_id),
        messages=messages,
    )
