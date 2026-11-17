import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import SessionDep
from app.comments.models import Comment
from app.config import settings
from app.news.models import News


def require_editor(x_api_key: Annotated[str | None, Header()] = None):
    if (
        not settings.admin_api_key
        or not x_api_key
        or not secrets.compare_digest(x_api_key, settings.admin_api_key)
    ):
        raise HTTPException(403, "Editor access required")


router = APIRouter(
    prefix="/editor", tags=["editor"], dependencies=[Depends(require_editor)]
)


class ArticleWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=100000)
    sport_id: str = Field(min_length=1, max_length=64)
    team_ids: list[str] = Field(default_factory=list, max_length=100)
    published_at: datetime | None = None
    source_url: HttpUrl | None = None
    source_name: str | None = Field(default=None, max_length=100)

    @field_validator("title", "summary", "body", "sport_id")
    @classmethod
    def strip_text(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Empty text")
        return value

    @field_validator("published_at")
    @classmethod
    def require_timezone(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Timezone is required")
        return value

    @field_validator("team_ids")
    @classmethod
    def validate_tags(cls, values):
        if any(not value.strip() or len(value) > 128 for value in values):
            raise ValueError("Invalid team ID")
        return list(dict.fromkeys(value.strip() for value in values))


class Visibility(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_hidden: bool


def article_data(article):
    return {
        column.name: getattr(article, column.name) for column in News.__table__.columns
    }


async def save(session, article, payload):
    values = payload.model_dump()
    values["source_url"] = str(payload.source_url) if payload.source_url else None
    for name, value in values.items():
        setattr(article, name, value)
    session.add(article)
    try:
        await session.flush()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(409, "Source URL already imported") from error
    await session.refresh(article)
    return article_data(article)


@router.post("/news", status_code=201)
async def create(payload: ArticleWrite, session: SessionDep):
    return await save(session, News(), payload)


@router.get("/news")
async def listing(
    session: SessionDep,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    articles = await session.scalars(
        select(News).order_by(News.id.desc()).limit(limit).offset(offset)
    )
    return [article_data(article) for article in articles]


@router.put("/news/{news_id}")
async def replace(news_id: int, payload: ArticleWrite, session: SessionDep):
    article = await session.get(News, news_id)
    if article is None:
        raise HTTPException(404, "News not found")
    return await save(session, article, payload)


@router.get("/comments")
async def moderation_queue(
    session: SessionDep,
    limit: int = Query(100, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    comments = await session.scalars(
        select(Comment).order_by(Comment.id.desc()).limit(limit).offset(offset)
    )
    return [
        {
            column.name: getattr(comment, column.name)
            for column in Comment.__table__.columns
        }
        for comment in comments
    ]


@router.patch("/comments/{comment_id}")
async def visibility(comment_id: int, payload: Visibility, session: SessionDep):
    comment = await session.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(404, "Comment not found")
    comment.is_hidden = payload.is_hidden
    await session.flush()
    return {"id": comment.id, "is_hidden": comment.is_hidden}
