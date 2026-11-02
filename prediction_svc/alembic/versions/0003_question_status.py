"""remember whether a question is still open and what the match fact was

Revision ID: 0003_question_status
Revises: 0002_questions
Create Date: 2026-11-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_question_status"
down_revision: str | None = "0002_questions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

question_status = sa.Enum("open", "closed", "withdrawn", name="question_status", native_enum=False, length=16)
question_outcome = sa.Enum("home", "draw", "away", name="question_outcome", native_enum=False, length=16)


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("status", question_status, server_default="open", nullable=False),
    )
    op.add_column("questions", sa.Column("factual_outcome", question_outcome, nullable=True))


def downgrade() -> None:
    op.drop_column("questions", "factual_outcome")
    op.drop_column("questions", "status")
