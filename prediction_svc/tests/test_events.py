import pytest
from pydantic import ValidationError

from app.events import SportsEvent


def match_payload(**overrides) -> dict:
    match = {
        "id": "match-1",
        "sport": "football",
        "home": {"id": "home", "name": "Home"},
        "away": {"id": "away", "name": "Away"},
        "starts_at": "2026-10-12T18:00:00Z",
        "status": "scheduled",
    }
    match.update(overrides)
    return match


def event_payload(event_type: str = "match.scheduled", **match_overrides) -> dict:
    return {
        "event_id": "evt-1",
        "event_type": event_type,
        "occurred_at": "2026-10-10T12:00:00Z",
        "version": 1,
        "match": match_payload(**match_overrides),
    }


@pytest.mark.parametrize(
    ("event_type", "match_overrides"),
    [
        ("match.scheduled", {"status": "scheduled"}),
        ("match.updated", {"status": "scheduled", "starts_at": "2026-10-13T18:00:00Z"}),
        ("match.started", {"status": "live"}),
        ("match.score_changed", {"status": "live", "score": {"home": 1, "away": 0}}),
        (
            "match.finished",
            {"status": "finished", "score": {"home": 2, "away": 1}, "outcome": "home"},
        ),
        ("match.cancelled", {"status": "cancelled"}),
        (
            "match.result_corrected",
            {"status": "finished", "score": {"home": 1, "away": 1}, "outcome": "draw"},
        ),
    ],
)
def test_seven_sports_events_are_accepted(event_type: str, match_overrides: dict) -> None:
    event = SportsEvent.model_validate(event_payload(event_type, **match_overrides))

    assert event.event_type.value == event_type
    assert event.match.id == "match-1"


@pytest.mark.parametrize("event_type", ["match.finished", "match.result_corrected"])
def test_result_events_require_score_and_outcome(event_type: str) -> None:
    with pytest.raises(ValidationError):
        SportsEvent.model_validate(event_payload(event_type, status="finished", score={"home": 1, "away": 0}))

    with pytest.raises(ValidationError):
        SportsEvent.model_validate(event_payload(event_type, status="finished", outcome="home"))


def test_score_change_requires_score() -> None:
    with pytest.raises(ValidationError):
        SportsEvent.model_validate(event_payload("match.score_changed", status="live"))
