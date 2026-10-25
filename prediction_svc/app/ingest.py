from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.events import SportsEvent
from app.matches import SCHEDULE_EVENTS, upsert_match
from app.models import ProcessedEvent


def record_event(session: Session, event: SportsEvent) -> bool:
    if session.get(ProcessedEvent, event.event_id) is not None:
        return False

    session.add(
        ProcessedEvent(
            event_id=event.event_id,
            event_type=event.event_type.value,
            match_external_id=event.match.id,
        )
    )
    return True


def store_event(session: Session, payload: dict) -> str:
    event = SportsEvent.model_validate(payload)
    if not record_event(session, event):
        return "skipped"

    upsert_match(session, event)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        if session.get(ProcessedEvent, event.event_id) is None:
            raise
        return "skipped"

    if event.event_type in SCHEDULE_EVENTS:
        return "accepted"
    return "recorded"
