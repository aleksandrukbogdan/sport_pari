from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta

from starlette.concurrency import run_in_threadpool

from app.clients.user_service import UserServiceClient
from app.news.models import News
from app.news.repository import PostgresNewsRepository
from app.recommendations.features import CANDIDATE_MAX_AGE_DAYS
from app.recommendations.model import NewsRanker
from app.recommendations.repository import PostgresViewRepository
from app.recommendations.schemas import Recommendation


@dataclass(frozen=True)
class RankedNews:
    news: News
    recommendation: Recommendation
    seen: bool
    popularity: float
    content: float = 0.0
    sport: float = 0.0
    comments_count: int = 0


class RecommendationService:
    def __init__(
        self,
        news: PostgresNewsRepository,
        views: PostgresViewRepository,
        users: UserServiceClient,
    ):
        self.news = news
        self.views = views
        self.users = users

    async def for_user(self, user_id: str, limit: int) -> list[Recommendation]:
        return [
            item.recommendation for item in await self.rank_for_user(user_id, limit)
        ]

    async def rank_for_user(
        self, user_id: str, limit: int, offset: int = 0
    ) -> list[RankedNews]:
        interests = await self.users.get_interests(user_id)
        rows = await self.news.list_candidates()
        articles = [news for news, _ in rows]
        if not articles:
            return []
        now = datetime.now(UTC)
        news_ids = [a.id for a in articles]
        interactions = await self.views.interactions(news_ids, now, user_id)
        popularity = await self.views.decayed_popularity(news_ids, now)
        ranked = await run_in_threadpool(
            self._rank,
            articles,
            interactions,
            interests,
            user_id,
            limit,
            offset,
            now,
            popularity,
        )
        counts = {article.id: count for article, count in rows}
        return [replace(item, comments_count=counts[item.news.id]) for item in ranked]

    @staticmethod
    def _rank(
        articles, interactions, interests, user_id, limit, offset, now, popularity
    ):
        ranker = NewsRanker()
        ranker.fit(articles, interactions, as_of=now, popularity=popularity)
        cutoff = now - timedelta(days=CANDIDATE_MAX_AGE_DAYS)
        fresh = [
            a
            for a in articles
            if (
                a.published_at.replace(tzinfo=UTC)
                if a.published_at.tzinfo is None
                else a.published_at
            )
            >= cutoff
        ]
        candidates = fresh or articles
        results = ranker.rank(
            user_id,
            candidates,
            sport_ids=interests.sport_ids if interests else (),
            team_ids=interests.team_ids if interests else (),
        )
        by_id = {a.id: a for a in articles}
        return [
            RankedNews(
                by_id[r.news_id],
                Recommendation(news_id=r.news_id, score=r.score, reason=r.reason),
                r.seen,
                r.popularity,
                r.content,
                r.sport,
            )
            for r in results[offset : offset + limit]
        ]
