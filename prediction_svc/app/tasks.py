from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import get_settings
from app.db import get_session_factory
from app.ingest import store_event
from app.sports_feed import fetch_sports_events, pull_sports_events


def ingest_payload(payload: dict, session: Session) -> str:
    return store_event(session, payload)


@celery_app.task(name="ingest_sports_event")
def ingest_sports_event(payload: dict) -> str:
    session = get_session_factory()()
    try:
        return ingest_payload(payload, session)
    finally:
        session.close()


@celery_app.task(name="poll_sports_events")
def poll_sports_events() -> dict[str, int]:
    events = fetch_sports_events(get_settings().sports_events_url)
    session = get_session_factory()()
    try:
        return pull_sports_events(session, events)
    finally:
        session.close()
