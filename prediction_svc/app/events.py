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

    @model_validator(mode="before")
    @classmethod
    def accept_flat_sports_message(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "match" not in data and "match_id" in data:
            data["match"] = {
                "id": data.get("match_id"),
                "sport": data.get("sport"),
                "home": data.get("home"),
                "away": data.get("away"),
                "starts_at": data.get("starts_at"),
                "status": data.get("status"),
                "score": data.get("score"),
                "outcome": data.get("outcome"),
            }
        match = data.get("match")
        if isinstance(match, dict):
            normalized = dict(match)
            if "id" in normalized and normalized["id"] is not None:
                normalized["id"] = str(normalized["id"])
            for side in ("home", "away"):
                team = normalized.get(side)
                if isinstance(team, dict) and "id" in team and team["id"] is not None:
                    normalized[side] = {**team, "id": str(team["id"])}
            data["match"] = normalized
        return data

    @model_validator(mode="after")
    def result_events_include_score_and_outcome(self) -> Self:
        needs_result = self.event_type in {EventType.finished, EventType.result_corrected}
        if needs_result and (self.match.score is None or self.match.outcome is None):
            raise ValueError("match.finished and match.result_corrected require score and outcome")
        if self.event_type is EventType.score_changed and self.match.score is None:
            raise ValueError("match.score_changed requires score")
        return self
