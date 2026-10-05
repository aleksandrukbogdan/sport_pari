from app.comments.models import Comment


class PostgresCommentRepository:
    """Comment thread under one news item. Oldest first.

    Creating a comment first checks that the news exists.
    Threads stay flat: no parent_id until moderation and replies are in scope.
    """

    async def list_for_news(
        self,
        news_id: int,
        *,
        limit: int,
        offset: int,
    ) -> list[Comment]:
        raise NotImplementedError("PostgresCommentRepository.list_for_news")

    async def add(self, comment: Comment) -> Comment:
        raise NotImplementedError("PostgresCommentRepository.add")
