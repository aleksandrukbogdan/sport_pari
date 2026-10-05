from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class NewsView(Base):
    """One opening of an article.

    Comments are not copied here. The ranker reads them from the comments
    table, otherwise the same action would be counted twice.
    The client or the BFF sends this event when the article page opens.
    There is no analytics bus in this skeleton. If one appears later, this
    table becomes a consumer of that stream.
    """

    __tablename__ = "news_views"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    news_id: Mapped[int] = mapped_column(
        ForeignKey("news.id", ondelete="CASCADE"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
