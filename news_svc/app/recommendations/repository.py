from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import NewsNotFound
from app.news.models import News
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

    async def seen_news_ids(self, user_id: str) -> set[int]:
        rows = await self.session.scalars(
            select(NewsView.news_id).where(NewsView.user_id == user_id)
        )
        return set(rows.all())
