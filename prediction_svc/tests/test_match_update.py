from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models import Match
from app.tasks import ingest_sports_event
from tests.test_events import event_payload
from tests.test_ingest import bind_sqlite
from tests.test_matches import as_utc


def test_update_moves_kickoff_and_replay_does_not_duplicate_the_match(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    scheduled = event_payload()
    updated = event_payload("match.updated", starts_at="2026-10-13T18:00:00Z")
    updated["event_id"] = "evt-2"
    updated["version"] = 2

    assert ingest_sports_event.delay(scheduled).get() == "accepted"
    assert ingest_sports_event.delay(updated).get() == "accepted"
    assert ingest_sports_event.delay(updated).get() == "skipped"

    with factory() as session:
        count = session.scalar(select(func.count()).select_from(Match))
        match = session.scalar(select(Match).where(Match.external_id == "match-1"))
        assert count == 1
        assert match is not None
        assert match.version == 2
        assert as_utc(match.starts_at) == datetime(2026, 10, 13, 18, 0, tzinfo=timezone.utc)
