from app.clients.user_service import UserInterests, UserServiceClient
from app.news.repository import PostgresNewsRepository
from app.recommendations.repository import PostgresViewRepository
from app.recommendations.schemas import Recommendation

_CANDIDATE_LIMIT = 50


class RecommendationService:
    """Короткий список опубликованных материалов.

    Зависимости приходят снаружи, сервис их не создаёт.
    База выдачи — уже опубликованная лента, не отдельный ранкер.
    Интересы, если сервис пользователей ответил, поднимают свои виды спорта наверх.
    Уже открытое остаётся в списке, но уходит ниже: иначе после одного просмотра
    блок может опустеть.
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
        interests = await self.users.get_interests(user_id)
        rows = await self.news.list_published(
            sport_id=None,
            limit=_CANDIDATE_LIMIT,
            offset=0,
        )
        seen = await self.views.seen_news_ids(user_id)
        ordered = sorted(rows, key=lambda row: _sort_key(row[0].id, row[0].sport_id, seen, interests))
        return [_recommendation(news, seen, interests) for news, _count in ordered[:limit]]


def _matches(sport_id: str, interests: UserInterests | None) -> bool:
    return bool(interests and interests.sport_ids and sport_id in interests.sport_ids)


def _sort_key(
    news_id: int,
    sport_id: str,
    seen: set[int],
    interests: UserInterests | None,
) -> tuple[bool, bool]:
    return (news_id in seen, not _matches(sport_id, interests))


def _recommendation(news, seen: set[int], interests: UserInterests | None) -> Recommendation:
    matched = _matches(news.sport_id, interests)
    if matched and news.id not in seen:
        score = 1.0
    elif news.id not in seen:
        score = 0.5
    else:
        score = 0.2
    return Recommendation(
        news_id=news.id,
        score=score,
        reason="sport" if matched else "popularity",
    )
