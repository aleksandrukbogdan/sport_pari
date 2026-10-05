from app.news.models import News


class PostgresNewsRepository:
    """Read path for the feed and the article page.

    Queries are not written yet. The feed is published rows only,
    newest first, optional filter by catalog sport_id.
    comments_count is a subquery, not a loaded comment collection.
    """

    async def list_published(
        self,
        *,
        sport_id: str | None,
        limit: int,
        offset: int,
    ) -> list[tuple[News, int]]:
        raise NotImplementedError("PostgresNewsRepository.list_published")

    async def get(self, news_id: int) -> tuple[News, int] | None:
        raise NotImplementedError("PostgresNewsRepository.get")
