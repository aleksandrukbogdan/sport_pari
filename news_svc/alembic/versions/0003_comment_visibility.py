"""add comment visibility

Revision ID: 0003_comment_visibility
Revises: 0002_news_views
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_comment_visibility"
down_revision = "0002_news_views"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "comments",
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("comments", "is_hidden")
