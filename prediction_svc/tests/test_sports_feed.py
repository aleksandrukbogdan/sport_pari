import io
import json

from sqlalchemy import select

from app.models import Match, MatchStatus
from app.sports_feed import fetch_sports_events, pull_sports_events
from app.tasks import poll_sports_events
from tests.test_events import event_payload
from tests.test_ingest import bind_sqlite


class _Body(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False


def test_pull_reads_the_sports_list_once_and_skips_it_on_the_next_pass(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    scheduled = event_payload()
    finished = event_payload(
        "match.finished",
        status="finished",
        score={"home": 2, "away": 1},
        outcome="home",
    )
    finished["event_id"] = "evt-finished"
    finished["occurred_at"] = "2026-10-12T20:00:00Z"
    monkeypatch.setattr("app.tasks.fetch_sports_events", lambda url: [scheduled, finished])

    assert poll_sports_events.delay().get() == {"accepted": 1, "recorded": 1, "skipped": 0}
    assert poll_sports_events.delay().get() == {"accepted": 0, "recorded": 0, "skipped": 2}

    with factory() as session:
        match = session.scalar(select(Match).where(Match.external_id == "match-1"))
        assert match is not None
        assert match.status == MatchStatus.finished
        assert match.score_home == 2


def test_pull_counts_each_new_event(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    session = factory()

    counts = pull_sports_events(session, [event_payload()])

    assert counts == {"accepted": 1, "recorded": 0, "skipped": 0}
    session.close()


def test_fetch_rejects_a_response_that_is_not_a_list(monkeypatch) -> None:
    monkeypatch.setattr("app.sports_feed.urlopen", lambda url, timeout: _Body(json.dumps({}).encode()))

    try:
        fetch_sports_events("http://sports/events")
    except ValueError as exc:
        assert str(exc) == "sports events response must be a list"
    else:
        raise AssertionError("expected a list")
