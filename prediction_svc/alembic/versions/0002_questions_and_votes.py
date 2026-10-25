"""add yes/no questions and vote history

Revision ID: 0002_questions
Revises: 0001_init
Create Date: 2026-10-25

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_questions"
down_revision: Union[str, None] = "0001_init"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

question_kind = sa.Enum("match", "event", name="question_kind", native_enum=False, length=16)
vote_choice = sa.Enum("yes", "no", name="vote_choice", native_enum=False, length=8)


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("kind", question_kind, nullable=False),
        sa.Column("match_external_id", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_questions_kind", "questions", ["kind"])

    op.create_table(
        "vote_casts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("choice", vote_choice, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vote_casts_question_id", "vote_casts", ["question_id"])
    op.create_index("ix_vote_casts_user_id", "vote_casts", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_vote_casts_user_id", table_name="vote_casts")
    op.drop_index("ix_vote_casts_question_id", table_name="vote_casts")
    op.drop_table("vote_casts")
    op.drop_index("ix_questions_kind", table_name="questions")
    op.drop_table("questions")
