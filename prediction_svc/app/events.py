import enum
from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from app.models import MatchStatus, Outcome


class EventType(enum.StrEnum):
    scheduled = "match.scheduled"
    updated = "match.updated"
    started = "match.started"
    score_changed = "match.score_changed"
    finished = "match.finished"
    cancelled = "match.cancelled"
    result_corrected = "match.result_corrected"


class TeamRef(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)


class Score(BaseModel):
    home: int = Field(ge=0)
    away: int = Field(ge=0)


class MatchSnapshot(BaseModel):
    id: str = Field(min_length=1)
    sport: str = Field(min_length=1)
    home: TeamRef
    away: TeamRef
    starts_at: datetime
    status: MatchStatus
    score: Score | None = None
    outcome: Outcome | None = None


class SportsEvent(BaseModel):
    event_id: str = Field(min_length=1)
    event_type: EventType
    occurred_at: datetime
    version: int = Field(ge=0)
    match: MatchSnapshot

    @model_validator(mode="after")
    def result_events_include_score_and_outcome(self) -> Self:
        needs_result = self.event_type in {EventType.finished, EventType.result_corrected}
        if needs_result and (self.match.score is None or self.match.outcome is None):
            raise ValueError("match.finished and match.result_corrected require score and outcome")
        if self.event_type is EventType.score_changed and self.match.score is None:
            raise ValueError("match.score_changed requires score")
        return self
