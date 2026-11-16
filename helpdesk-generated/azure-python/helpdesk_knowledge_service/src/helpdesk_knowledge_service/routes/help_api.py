"""HelpAPI route handlers."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path
from fastapi import status as http_status
from pydantic import BeforeValidator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from helpdesk_knowledge_service._domain_formats import _cruftfree_require_uuid_text
from helpdesk_knowledge_service.errors.problem_details import register_path_field_names
from helpdesk_knowledge_service.functions import card_of, cards_of, published_article
from helpdesk_knowledge_service.knowledge_db.session import get_knowledge_db_db
from helpdesk_knowledge_service.models.knowledge_db.article import Article
from helpdesk_knowledge_service.schemas.article_card import ArticleCard
from helpdesk_knowledge_service.schemas.article_page import ArticlePage
from helpdesk_knowledge_service.schemas.knowledge_db.article import ArticleUpdate
from helpdesk_knowledge_service.schemas.vote_request import VoteRequest
from helpdesk_knowledge_service.services.knowledge_db.article_service import (
    ArticleService,
)

router = APIRouter(
    prefix="/api/v1/help",
    tags=["HelpAPI"],
)

# The path parameters this router binds, wire name -> the placeholder the DSL
# declares: a path validation error names the placeholder, never the wire name.
register_path_field_names(
    {
        "id": "id",
        "query": "query",
    }
)


@router.get("/articles")
async def get_articles(
    *,
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
) -> list[ArticleCard]:
    return cards_of(
        list(
            (
                await knowledge_db.execute(
                    select(Article)
                    .where(Article.published == True)
                    .order_by(Article.helpful.desc())
                    .limit(40)
                )
            )
            .scalars()
            .all()
        )
    )


@router.post(
    "/articles/{id}/vote",
    response_model=ArticleCard,
    status_code=http_status.HTTP_201_CREATED,
)
async def post_articles_by_id_vote(
    *,
    request: Annotated[VoteRequest, Body()],
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
) -> ArticleCard:
    found: Article = await published_article(id_, knowledge_db, _commit=True)
    if request.helped:
        found.helpful = found.helpful + 1
    else:
        found.not_helpful = found.not_helpful + 1
    _article_svc = ArticleService(knowledge_db)
    found = await _article_svc.update(
        found.id, ArticleUpdate(helpful=found.helpful, notHelpful=found.not_helpful)
    )
    return card_of(found)


@router.get("/search/{query}")
async def get_search_by_query(
    *,
    query: Annotated[str, Path()],
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
) -> list[ArticleCard]:
    return cards_of(
        list(
            (
                await knowledge_db.execute(
                    select(Article)
                    .where(
                        func.to_tsvector(
                            "english",
                            func.coalesce(Article.title, "")
                            + " "
                            + func.coalesce(Article.summary, "")
                            + " "
                            + func.coalesce(Article.body, ""),
                        ).op("@@")(func.plainto_tsquery("english", query))
                    )
                    .where(Article.published == True)
                    .limit(20)
                )
            )
            .scalars()
            .all()
        )
    )


@router.get("/articles/{id}", response_model=ArticlePage)
async def get_articles_by_id(
    *,
    id_: Annotated[
        uuid.UUID, BeforeValidator(_cruftfree_require_uuid_text), Path(alias="id")
    ],
    knowledge_db: AsyncSession = Depends(get_knowledge_db_db),
) -> ArticlePage:
    found: Article = await published_article(id_, knowledge_db, _commit=True)
    return ArticlePage(
        article=card_of(found),
        body=found.body,
        helpful=found.helpful,
        updatedAt=found.updated_at,
    )
