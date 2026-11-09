from datetime import UTC, datetime

from sqlalchemy import Float, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NewsNotFound
from app.news.models import News
from app.recommendations.features import POPULARITY_HALF_LIFE_HOURS
from app.recommendations.models import NewsView


class PostgresViewRepository:
    """Журнал открытий материала.

    Комментарий сюда не копируется: он уже лежит в comments.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, view: NewsView) -> NewsView:
        published = await self.session.scalar(
            select(News.id).where(
                News.id == view.news_id,
                News.published_at.is_not(None),
            )
        )
        if published is None:
            raise NewsNotFound
        self.session.add(view)
        await self.session.flush()
        await self.session.refresh(view)
        return view

    async def seen_news_ids(self, user_id: str, news_ids: list[int]) -> set[int]:
        rows = await self.session.scalars(
            select(NewsView.news_id)
            .where(NewsView.user_id == user_id, NewsView.news_id.in_(news_ids))
            .distinct()
        )
        return set(rows.all())

    async def decayed_popularity(self, news_ids: list[int]) -> dict[int, float]:
        now = datetime.now(UTC)
        if self.session.get_bind().dialect.name == "sqlite":
            age_hours = (func.julianday(now) - func.julianday(NewsView.created_at)) * 24
        else:
            created_epoch = extract("epoch", NewsView.created_at).cast(Float)
            age_hours = (now.timestamp() - created_epoch) / 3600

        weight = func.power(0.5, age_hours / POPULARITY_HALF_LIFE_HOURS)
        stmt = (
            select(NewsView.news_id, func.sum(weight))
            .where(NewsView.news_id.in_(news_ids), NewsView.created_at <= now)
            .group_by(NewsView.news_id)
        )
        return {news_id: float(total) for news_id, total in await self.session.execute(stmt)}
