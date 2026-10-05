from app.recommendations.models import NewsView


class PostgresViewRepository:
    """Журнал открытий материала. Агрегация живёт в ранкере, не в этой таблице."""

    async def add(self, view: NewsView) -> NewsView:
        raise NotImplementedError("PostgresViewRepository.add")

    async def seen_news_ids(self, user_id: str) -> set[int]:
        raise NotImplementedError("PostgresViewRepository.seen_news_ids")
