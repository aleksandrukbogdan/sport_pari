from app.clients.user_service import UserServiceClient
from app.news.repository import PostgresNewsRepository
from app.recommendations.model import NewsRanker
from app.recommendations.repository import PostgresViewRepository
from app.recommendations.schemas import Recommendation


class RecommendationService:
    """Короткий список для новостного блока.

    Когда заглушки станут реальными:
    1. Любимые виды спорта и команды из сервиса пользователей.
    2. Свежие опубликованные материалы из PostgresNewsRepository.
    3. Убрать id из PostgresViewRepository.seen_news_ids.
    4. NewsRanker.rank. Без истории и без интересов — затухающая общая
       популярность, чтобы новый пользователь всё равно видел ленту.
    """

    def __init__(self) -> None:
        self.ranker = NewsRanker()
        self.users = UserServiceClient()
        self.news = PostgresNewsRepository()
        self.views = PostgresViewRepository()

    async def for_user(self, user_id: str, limit: int) -> list[Recommendation]:
        raise NotImplementedError("RecommendationService.for_user")
