from dataclasses import dataclass

from app.clients.user_service import UserInterests, UserServiceClient
from app.news.models import News
from app.news.repository import PostgresNewsRepository
from app.recommendations.repository import PostgresViewRepository
from app.recommendations.schemas import Recommendation

_CANDIDATE_LIMIT = 50


@dataclass(frozen=True)
class RankedNews:
    news: News
    recommendation: Recommendation
    seen: bool
    popularity: float


class RecommendationService:
    """Короткий список опубликованных материалов.

    Зависимости приходят снаружи, сервис их не создаёт.
    Совпадение по виду спорта поднимает материал среди прочитанных или непрочитанных.
    Популярность определяет порядок внутри каждой группы.
    """

    def __init__(
        self,
        news: PostgresNewsRepository,
        views: PostgresViewRepository,
        users: UserServiceClient,
    ) -> None:
        self.news = news
        self.views = views
        self.users = users

    async def for_user(self, user_id: str, limit: int) -> list[Recommendation]:
        return [item.recommendation for item in await self.rank_for_user(user_id, limit)]

    async def rank_for_user(self, user_id: str, limit: int) -> list[RankedNews]:
        interests = await self.users.get_interests(user_id)
        rows = await self.news.list_published(
            sport_id=None,
            limit=_CANDIDATE_LIMIT,
            offset=0,
        )
        if not rows:
            return []
        news_ids = [news.id for news, _ in rows]
        seen = await self.views.seen_news_ids(user_id, news_ids)
        popularity = await self.views.decayed_popularity(news_ids)
        ranked = [
            _rank_article(news, news.id in seen, interests, popularity.get(news.id, 0.0))
            for news, _ in rows
        ]
        return sorted(ranked, key=lambda item: item.recommendation.score, reverse=True)[:limit]


def _matches(sport_id: str, interests: UserInterests | None) -> bool:
    return bool(interests and interests.sport_ids and sport_id in interests.sport_ids)


def _rank_article(
    news: News,
    seen: bool,
    interests: UserInterests | None,
    popularity: float,
) -> RankedNews:
    matched = _matches(news.sport_id, interests)
    if seen:
        base_score = 0.3 if matched else 0.2
    else:
        base_score = 0.9 if matched else 0.5
    # The popularity bonus stays within the gap between priority groups.
    popularity_bonus = 0.1 * popularity / (1 + popularity)
    recommendation = Recommendation(
        news_id=news.id,
        score=base_score + popularity_bonus,
        reason="sport" if matched else "popularity",
    )
    return RankedNews(news, recommendation, seen, popularity)
