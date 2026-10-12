import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.celery_app import celery_app
from app.consumer import handle_message
from app.db import Base
from app.models import Match, ProcessedEvent
from app.tasks import ingest_sports_event
from tests.test_events import event_payload


def bind_sqlite(monkeypatch):
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr("app.tasks.get_session_factory", lambda: factory)
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
    return factory


def test_same_event_id_is_accepted_once(monkeypatch) -> None:
    bind_sqlite(monkeypatch)
    payload = event_payload()

    assert ingest_sports_event.delay(payload).get() == "accepted"
    assert ingest_sports_event.delay(payload).get() == "skipped"


def test_consumer_forwards_message_without_creating_a_match(monkeypatch) -> None:
    factory = bind_sqlite(monkeypatch)
    raw = json.dumps(event_payload("match.started", status="live")).encode()

    handle_message(raw)

    with factory() as session:
        stored = session.get(ProcessedEvent, "evt-1")
        assert stored is not None
        assert stored.event_type == "match.started"
        assert stored.match_external_id == "match-1"
        assert session.query(Match).count() == 0
