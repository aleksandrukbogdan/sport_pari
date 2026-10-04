import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


class MatchStatus(enum.StrEnum):
    scheduled = "scheduled"
    live = "live"
    finished = "finished"
    cancelled = "cancelled"


class Outcome(enum.StrEnum):
    home = "home"
    draw = "draw"
    away = "away"


class PredictionStatus(enum.StrEnum):
    open = "open"
    locked = "locked"
    won = "won"
    lost = "lost"
    void = "void"
    invalid = "invalid"


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id: Mapped[str] = mapped_column(String(128), unique=True)
    sport: Mapped[str] = mapped_column(String(64))
    home_id: Mapped[str] = mapped_column(String(128))
    home_name: Mapped[str] = mapped_column(String(256))
    away_id: Mapped[str] = mapped_column(String(128))
    away_name: Mapped[str] = mapped_column(String(256))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status", native_enum=False, length=32),
        index=True,
    )
    score_home: Mapped[int | None] = mapped_column(Integer)
    score_away: Mapped[int | None] = mapped_column(Integer)
    outcome: Mapped[Outcome | None] = mapped_column(
        Enum(Outcome, name="match_outcome", native_enum=False, length=16)
    )
    version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserPrediction(Base):
    __tablename__ = "user_predictions"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="uq_user_prediction_match"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    match_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("matches.id", ondelete="RESTRICT")
    )
    pick: Mapped[Outcome] = mapped_column(
        Enum(Outcome, name="prediction_pick", native_enum=False, length=16)
    )
    status: Mapped[PredictionStatus] = mapped_column(
        Enum(PredictionStatus, name="prediction_status", native_enum=False, length=16),
        default=PredictionStatus.open,
        server_default=PredictionStatus.open.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    match_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("matches.id", ondelete="RESTRICT")
    )
    kind: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProcessedEvent(Base):
    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(64))
    match_external_id: Mapped[str | None] = mapped_column(String(128))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
