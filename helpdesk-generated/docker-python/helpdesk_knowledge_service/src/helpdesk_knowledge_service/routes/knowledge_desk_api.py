"""KnowledgeDeskAPI route handlers."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query
from fastapi import status as http_status
from pydantic import BeforeValidator
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_knowledge_service._domain_formats import _cruftfree_require_uuid_text
from helpdesk_knowledge_service.auth import require_route
from helpdesk_knowledge_service.enums.ticket_topic import TicketTopic
from helpdesk_knowledge_service.errors.problem_details import (
    register_path_field_names,
    repeated_query_keys_guard,
)
from helpdesk_knowledge_service.knowledge_db.session import get_knowledge_db_db
from helpdesk_knowledge_service.models.knowledge_db.article import Article
from helpdesk_knowledge_service.schemas.knowledge_db.article import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
)
from helpdesk_knowledge_service.schemas.page import Page
from helpdesk_knowledge_service.schemas.page_request import PageRequest
from helpdesk_knowledge_service.services.knowledge_db.article_service import (
    ArticleService,
)

router = APIRouter(
    prefix="/api/v1/desk",
    tags=["KnowledgeDeskAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "id": "id",
    }
)


@router.get("/articles", response_model=Page[ArticleResponse])
async def list_articles(
    *,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    title: Annotated[str | None, Query()] = None,
    topic: Annotated[TicketTopic | None, Query()] = None,
    published: Annotated[bool | None, Query()] = None,
    _repeated_query_keys: None = Depends(
        repeated_query_keys_guard(["skip", "limit", "title", "topic", "published"])
    ),
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> Page[Article]:
    page = PageRequest(offset=skip, limit=limit)
    service = ArticleService(knowledge_db)
    return await service.get_all(page, title=title, topic=topic, published=published)


@router.post(
    "/articles",
    response_model=ArticleResponse,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_article(
    *,
    body: Annotated[ArticleCreate, Body()],
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> Article:
    service = ArticleService(knowledge_db)
    return await service.create(body)


@router.get("/articles/{id}", response_model=ArticleResponse)
async def get_article(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> Article:
    service = ArticleService(knowledge_db)
    return await service.get(id_)


@router.put("/articles/{id}", response_model=ArticleResponse)
async def update_article(
    *,
    body: Annotated[ArticleUpdate, Body()],
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> Article:
    service = ArticleService(knowledge_db)
    return await service.update(id_, body)


@router.delete("/articles/{id}", status_code=http_status.HTTP_204_NO_CONTENT)
async def delete_article(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
    current_user=Depends(
        require_route(
            providers=["identity", "test_auth"],
            roles=["agent"],
            principal_types=["human"],
        )
    ),
) -> None:
    service = ArticleService(knowledge_db)
    await service.delete(id_)
