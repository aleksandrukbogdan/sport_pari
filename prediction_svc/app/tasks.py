from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db import get_session_factory
from app.events import SportsEvent
from app.ingest import record_event
from app.matches import upsert_match


def ingest_payload(payload: dict, session: Session) -> str:
    event = SportsEvent.model_validate(payload)
    if not record_event(session, event):
        return "skipped"

    upsert_match(session, event)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        return "skipped"
    return "accepted"


@celery_app.task(name="ingest_sports_event")
def ingest_sports_event(payload: dict) -> str:
    session = get_session_factory()()
    try:
        return ingest_payload(payload, session)
    finally:
        session.close()
