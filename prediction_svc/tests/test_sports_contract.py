import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.events import SportsEvent
from app.ingest import store_event
from app.models import ProcessedEvent
from tests.test_ingest import bind_sqlite

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_flat_sports_messages_match_the_sender() -> None:
    scheduled = SportsEvent.model_validate(load_fixture("sports_scheduled.json"))
    finished = SportsEvent.model_validate(load_fixture("sports_finished.json"))

    assert scheduled.match.id == "15"
    assert scheduled.match.home.id == "1"
    assert scheduled.match.away.name == "South"
    assert finished.match.score is not None
    assert finished.match.score.home == 2
    assert finished.match.outcome == "home"


def test_flat_finished_message_requires_outcome() -> None:
    payload = load_fixture("sports_finished.json")
    payload["outcome"] = None

    with pytest.raises(ValidationError):
        SportsEvent.model_validate(payload)


def test_event_id_conflict_on_commit_is_skipped(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    payload = load_fixture("sports_scheduled.json")
    event_id = payload["event_id"]

    with factory() as session:
        def lose_the_race() -> None:
            winner = factory()
            winner.add(
                ProcessedEvent(
                    event_id=event_id,
                    event_type="match.scheduled",
                    match_external_id="15",
                )
            )
            winner.commit()
            winner.close()
            raise IntegrityError("INSERT", {}, Exception("processed_events_pkey"))

        session.commit = lose_the_race  # type: ignore[method-assign]
        assert store_event(session, payload) == "skipped"
        assert session.get(ProcessedEvent, event_id) is not None


def test_other_integrity_error_is_not_reported_as_a_duplicate(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    payload = load_fixture("sports_scheduled.json")

    with factory() as session:
        def fail_on_another_constraint() -> None:
            raise IntegrityError("INSERT", {}, Exception("matches_external_id_key"))

        session.commit = fail_on_another_constraint  # type: ignore[method-assign]
        with pytest.raises(IntegrityError):
            store_event(session, payload)
