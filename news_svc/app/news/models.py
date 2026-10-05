from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
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

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text())
    sport_id: Mapped[str] = mapped_column(String(64), index=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
