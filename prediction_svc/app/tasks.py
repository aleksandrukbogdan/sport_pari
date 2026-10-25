from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.db import get_session_factory
from app.ingest import store_event


def ingest_payload(payload: dict, session: Session) -> str:
    return store_event(session, payload)


@celery_app.task(name="ingest_sports_event")
def ingest_sports_event(payload: dict) -> str:
    session = get_session_factory()()
    try:
        return ingest_payload(payload, session)
    finally:
        session.close()
