"""remember when the stored match copy was last taken from Sports

Revision ID: 0004_match_source_time
Revises: 0003_question_status
Create Date: 2026-11-11

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_match_source_time"
down_revision: str | None = "0003_question_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("source_occurred_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "source_occurred_at")
