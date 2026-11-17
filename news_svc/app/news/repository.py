from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.models import Comment
from app.news.models import News


class PostgresNewsRepository:
    """Published news, newest first.

    A row without published_at is a draft and stays out of the feed.
    comments_count includes only visible comments.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _published(self):
        comments_count = (
            select(func.count(Comment.id))
            .where(Comment.news_id == News.id, Comment.is_hidden.is_(False))
            .correlate(News)
            .scalar_subquery()
        )
        return select(News, comments_count).where(
            News.published_at <= datetime.now(UTC)
        )

    def _filtered(self, sport_id=None, q=None):
        stmt = self._published()
        if sport_id:
            stmt = stmt.where(News.sport_id == sport_id)
        if q:
            pattern = (
                "%"
                + q.strip()
                .replace("\\", "\\\\")
                .replace("%", "\\%")
                .replace("_", "\\_")
                + "%"
            )
            stmt = stmt.where(
                or_(
                    News.title.ilike(pattern, escape="\\"),
                    News.body.ilike(pattern, escape="\\"),
                )
            )
        return stmt

    async def list_published(
        self,
        *,
        sport_id: str | None,
        limit: int,
        offset: int,
        q: str | None = None,
    ) -> list[tuple[News, int]]:
        stmt = self._filtered(sport_id, q).order_by(
            News.published_at.desc(), News.id.desc()
        )
        rows = await self.session.execute(stmt.limit(limit).offset(offset))
        return [(news, int(count)) for news, count in rows.all()]

    async def get(self, news_id: int) -> tuple[News, int] | None:
        stmt = self._published().where(News.id == news_id)
        row = (await self.session.execute(stmt)).one_or_none()
        if row is None:
            return None
        news, count = row
        return news, int(count)

    async def sport_counts(self) -> dict[str, int]:
        rows = await self.session.execute(
            select(News.sport_id, func.count(News.id))
            .where(News.published_at <= datetime.now(UTC))
            .group_by(News.sport_id)
        )
        return dict(rows.all())

    async def count_published(self, *, sport_id=None, q=None) -> int:
        query = self._filtered(sport_id, q)
        return await self.session.scalar(
            select(func.count()).select_from(query.subquery())
        )

    async def list_candidates(self) -> list[tuple[News, int]]:
        window = (
            select(
                News.id,
                func.row_number()
                .over(
                    partition_by=News.sport_id,
                    order_by=(News.published_at.desc(), News.id.desc()),
                )
                .label("position"),
            )
            .where(News.published_at <= datetime.now(UTC))
            .subquery()
        )
        ids = select(window.c.id).where(window.c.position <= 75)
        query = (
            self._published()
            .where(News.id.in_(ids))
            .order_by(News.published_at.desc(), News.id.desc())
            .limit(1000)
        )
        rows = await self.session.execute(query)
        return [(article, int(count)) for article, count in rows]
