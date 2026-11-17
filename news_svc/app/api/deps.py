from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.user_service import UserServiceClient
from app.comments.repository import PostgresCommentRepository
from app.config import settings
from app.db import get_session
from app.news.repository import PostgresNewsRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_news_repository(session: SessionDep) -> PostgresNewsRepository:
    return PostgresNewsRepository(session)


def get_comment_repository(session: SessionDep) -> PostgresCommentRepository:
    return PostgresCommentRepository(session)


NewsRepo = Annotated[PostgresNewsRepository, Depends(get_news_repository)]
CommentRepo = Annotated[PostgresCommentRepository, Depends(get_comment_repository)]


def get_user_service() -> UserServiceClient:
    return UserServiceClient()


async def get_current_user_id(
    users: Annotated[UserServiceClient, Depends(get_user_service)],
    authorization: Annotated[str | None, Header()] = None,
    x_user_id: Annotated[str | None, Header()] = None,
) -> str:
    """Validate bearer tokens using user_svc; allow gateway IDs only when configured."""

    if authorization:
        if not authorization.lower().startswith("bearer "):
            raise HTTPException(401, "Bearer token required")
        return (await users.profile(authorization))["id"]
    if (
        settings.trust_gateway_headers
        and x_user_id
        and 0 < len(x_user_id.strip()) <= 64
    ):
        return x_user_id.strip()
    raise HTTPException(401, "Authorization is required")


CurrentUserId = Annotated[str, Depends(get_current_user_id)]
