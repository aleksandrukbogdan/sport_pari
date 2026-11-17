from datetime import UTC, datetime

from sqlalchemy import Float, extract, func, literal, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.comments.models import Comment
from app.errors import NewsNotFound
from app.news.models import News
from app.recommendations.features import EVENT_WEIGHT, POPULARITY_HALF_LIFE_HOURS
from app.recommendations.model import Interaction
from app.recommendations.models import NewsView


class PostgresViewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, view: NewsView) -> NewsView:
        published = await self.session.scalar(
            select(News.id).where(
                News.id == view.news_id, News.published_at <= datetime.now(UTC)
            )
        )
        if published is None:
            raise NewsNotFound
        self.session.add(view)
        await self.session.flush()
        await self.session.refresh(view)
        return view

    def _events(self, news_ids, as_of, user_id=None):
        views = select(
            NewsView.user_id.label("user_id"),
            NewsView.news_id,
            NewsView.created_at,
            literal("view").label("event_type"),
        ).where(
            NewsView.news_id.in_(news_ids),
            NewsView.created_at <= as_of,
        )
        comments = select(
            Comment.author_id.label("user_id"),
            Comment.news_id,
            Comment.created_at,
            literal("comment").label("event_type"),
        ).where(
            Comment.news_id.in_(news_ids),
            Comment.is_hidden.is_(False),
            Comment.created_at <= as_of,
        )
        if user_id is not None:
            views = views.where(NewsView.user_id == user_id)
            comments = comments.where(Comment.author_id == user_id)
        return union_all(views, comments).subquery()

    async def interactions(self, news_ids, as_of, user_id=None):
        events = self._events(news_ids, as_of, user_id)
        rows = await self.session.execute(select(events))
        return [
            Interaction(user, news, event_type, created)
            for user, news, created, event_type in rows
        ]

    async def decayed_popularity(
        self, news_ids: list[int], as_of: datetime
    ) -> dict[int, float]:
        from sqlalchemy import case

        events = self._events(news_ids, as_of)
        if self.session.get_bind().dialect.name == "sqlite":
            age_hours = (
                func.julianday(as_of) - func.julianday(events.c.created_at)
            ) * 24
        else:
            created_epoch = extract("epoch", events.c.created_at).cast(Float)
            age_hours = (as_of.timestamp() - created_epoch) / 3600
        event_weight = case(
            (events.c.event_type == "comment", EVENT_WEIGHT["comment"]),
            else_=EVENT_WEIGHT["view"],
        )
        weight = event_weight * func.power(0.5, age_hours / POPULARITY_HALF_LIFE_HOURS)
        stmt = select(events.c.news_id, func.sum(weight)).group_by(events.c.news_id)
        return {
            news_id: float(total) for news_id, total in await self.session.execute(stmt)
        }
