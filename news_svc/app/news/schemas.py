from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NewsCard(BaseModel):
    """Item of the feed. The block does not need the full body."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str
    sport_id: str
    published_at: datetime
    comments_count: int = 0


class NewsDetail(NewsCard):
    body: str
