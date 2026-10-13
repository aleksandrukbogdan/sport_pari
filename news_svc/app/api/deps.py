from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.repository import PostgresCommentRepository
from app.db import get_session
from app.news.repository import PostgresNewsRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_news_repository(session: SessionDep) -> PostgresNewsRepository:
    return PostgresNewsRepository(session)


def get_comment_repository() -> PostgresCommentRepository:
    return PostgresCommentRepository()


NewsRepo = Annotated[PostgresNewsRepository, Depends(get_news_repository)]
CommentRepo = Annotated[PostgresCommentRepository, Depends(get_comment_repository)]


def get_current_user_id(x_user_id: Annotated[str | None, Header()] = None) -> str:
    """Identity is the gateway's job.

    Inside the platform network the gateway forwards the authenticated user id.
    This service does not validate JWT and does not keep a users table.
    """

    if not x_user_id or not x_user_id.strip():
        raise HTTPException(status_code=401, detail="X-User-Id is required")
    return x_user_id.strip()


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
