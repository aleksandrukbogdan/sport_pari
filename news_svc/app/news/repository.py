from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.models import Comment
from app.news.models import News


class PostgresNewsRepository:
    """Published news, newest first.

    A row without published_at is a draft and stays out of the feed.
    comments_count is a subquery, not a loaded comment collection.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _published(self):
        comments_count = (
            select(func.count(Comment.id))
            .where(Comment.news_id == News.id)
            .correlate(News)
            .scalar_subquery()
        )
        return select(News, comments_count).where(News.published_at.is_not(None))

    async def list_published(
        self,
        *,
        sport_id: str | None,
        limit: int,
        offset: int,
    ) -> list[tuple[News, int]]:
        stmt = self._published().order_by(News.published_at.desc(), News.id.desc())
        if sport_id:
            stmt = stmt.where(News.sport_id == sport_id)
        rows = await self.session.execute(stmt.limit(limit).offset(offset))
        return [(news, int(count)) for news, count in rows.all()]

    async def get(self, news_id: int) -> tuple[News, int] | None:
        stmt = self._published().where(News.id == news_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        news, count = row
        return news, int(count)
