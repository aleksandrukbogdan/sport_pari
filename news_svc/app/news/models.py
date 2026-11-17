from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class News(Base):
    """Published material for the news block.

    sport_id is an id from the catalog service, not a local dictionary.
    A row is visible in the feed only when published_at is set.
    Article body stays plain text for now. If the layout becomes a tree of
    blocks, store that tree in JSONB instead of moving the service to a
    document database: comments and the feed sort stay relational.
    """

    __tablename__ = "news"
    __table_args__ = (Index("ux_news_source_url", "source_url", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text())
    sport_id: Mapped[str] = mapped_column(String(64), index=True)
    team_ids: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    source_url: Mapped[str | None] = mapped_column(String(2048))
    source_name: Mapped[str | None] = mapped_column(String(100))
    image_url: Mapped[str | None] = mapped_column(String(2048))
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
