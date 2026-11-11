from datetime import datetime, timezone

from sqlalchemy import select

from app.models import Match, MatchStatus
from app.tasks import ingest_sports_event
from tests.test_events import event_payload
from tests.test_ingest import bind_sqlite


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def test_scheduled_event_stores_one_match_copy(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)

    assert ingest_sports_event.delay(event_payload()).get() == "accepted"

    with factory() as session:
        matches = session.scalars(select(Match)).all()
        assert len(matches) == 1
        match = matches[0]
        assert match.external_id == "match-1"
        assert match.sport == "football"
        assert match.home_name == "Home"
        assert match.away_name == "Away"
        assert match.status == MatchStatus.scheduled
        assert match.version == 1
        assert as_utc(match.starts_at) == datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc)


def test_older_version_does_not_change_the_match(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    ingest_sports_event.delay(event_payload()).get()

    stale = event_payload("match.updated", starts_at="2026-10-20T18:00:00Z", home={"id": "home", "name": "Other"})
    stale["event_id"] = "evt-stale"
    stale["version"] = 0
    assert ingest_sports_event.delay(stale).get() == "accepted"

    with factory() as session:
        match = session.scalar(select(Match).where(Match.external_id == "match-1"))
        assert match is not None
        assert match.home_name == "Home"
        assert match.version == 1
        assert as_utc(match.starts_at) == datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc)


def test_earlier_event_does_not_overwrite_a_later_one(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    current = event_payload()
    current["occurred_at"] = "2026-10-11T12:00:00Z"
    ingest_sports_event.delay(current).get()

    stale = event_payload("match.updated", home={"id": "home", "name": "Other"})
    stale["event_id"] = "evt-stale"
    stale["occurred_at"] = "2026-10-09T12:00:00Z"
    assert ingest_sports_event.delay(stale).get() == "accepted"

    with factory() as session:
        match = session.scalar(select(Match).where(Match.external_id == "match-1"))
        assert match is not None
        assert match.home_name == "Home"


def test_finished_event_updates_score_status_and_outcome(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    ingest_sports_event.delay(event_payload()).get()

    finished = event_payload(
        "match.finished",
        status="finished",
        score={"home": 2, "away": 1},
        outcome="home",
    )
    finished["event_id"] = "evt-finished"
    finished["occurred_at"] = "2026-10-12T20:00:00Z"
    assert ingest_sports_event.delay(finished).get() == "recorded"

    with factory() as session:
        match = session.scalar(select(Match).where(Match.external_id == "match-1"))
        assert match is not None
        assert match.status == MatchStatus.finished
        assert match.score_home == 2
        assert match.score_away == 1
        assert match.outcome.value == "home"
