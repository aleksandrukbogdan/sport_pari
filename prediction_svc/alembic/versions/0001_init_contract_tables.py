"""create match, prediction, notification, and processed event tables

Revision ID: 0001_init
Revises:
Create Date: 2026-10-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_init"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

match_status = sa.Enum(
    "scheduled",
    "live",
    "finished",
    "cancelled",
    name="match_status",
    native_enum=False,
    length=32,
)
match_outcome = sa.Enum(
    "home", "draw", "away", name="match_outcome", native_enum=False, length=16
)
prediction_pick = sa.Enum(
    "home", "draw", "away", name="prediction_pick", native_enum=False, length=16
)
prediction_status = sa.Enum(
    "open",
    "locked",
    "won",
    "lost",
    "void",
    "invalid",
    name="prediction_status",
    native_enum=False,
    length=16,
)


def upgrade() -> None:
    op.create_table(
        "matches",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("sport", sa.String(length=64), nullable=False),
        sa.Column("home_id", sa.String(length=128), nullable=False),
        sa.Column("home_name", sa.String(length=256), nullable=False),
        sa.Column("away_id", sa.String(length=128), nullable=False),
        sa.Column("away_name", sa.String(length=256), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", match_status, nullable=False),
        sa.Column("score_home", sa.Integer(), nullable=True),
        sa.Column("score_away", sa.Integer(), nullable=True),
        sa.Column("outcome", match_outcome, nullable=True),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_index("ix_matches_status", "matches", ["status"])

    op.create_table(
        "user_predictions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("pick", prediction_pick, nullable=False),
        sa.Column("status", prediction_status, server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "match_id", name="uq_user_prediction_match"),
    )
    op.create_index("ix_user_predictions_user_id", "user_predictions", ["user_id"])

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])

    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("match_external_id", sa.String(length=128), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("processed_events")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_user_predictions_user_id", table_name="user_predictions")
    op.drop_table("user_predictions")
    op.drop_index("ix_matches_status", table_name="matches")
    op.drop_table("matches")
