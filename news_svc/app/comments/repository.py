from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.models import Comment
from app.errors import NewsNotFound
from app.news.models import News


class PostgresCommentRepository:
    """Flat thread under one published article, oldest first.

    A missing or unpublished article raises NewsNotFound for both reads and writes.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _require_published(self, news_id: int) -> None:
        exists = await self.session.scalar(
            select(News.id).where(News.id == news_id, News.published_at.is_not(None))
        )
        if exists is None:
            raise NewsNotFound

    async def list_for_news(
        self,
        news_id: int,
        *,
        limit: int,
        offset: int,
    ) -> list[Comment]:
        await self._require_published(news_id)
        stmt = (
            select(Comment)
            .where(Comment.news_id == news_id)
            .order_by(Comment.created_at.asc(), Comment.id.asc())
            .limit(limit)
            .offset(offset)
        )
        return list(await self.session.scalars(stmt))

    async def add(self, comment: Comment) -> Comment:
        await self._require_published(comment.news_id)
        self.session.add(comment)
        await self.session.flush()
        await self.session.refresh(comment)
        return comment
