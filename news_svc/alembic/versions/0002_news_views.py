"""create news_views

Revision ID: 0002_news_views
Revises: 0001_news_comments
Create Date: 2026-10-27

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_news_views"
down_revision: Union[str, Sequence[str], None] = "0001_news_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "news_views",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("news_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["news_id"], ["news.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_news_views_user_id", "news_views", ["user_id"])
    op.create_index("ix_news_views_news_id", "news_views", ["news_id"])
    op.create_index("ix_news_views_created_at", "news_views", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_news_views_created_at", table_name="news_views")
    op.drop_index("ix_news_views_news_id", table_name="news_views")
    op.drop_index("ix_news_views_user_id", table_name="news_views")
    op.drop_table("news_views")
