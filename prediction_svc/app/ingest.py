from sqlalchemy.orm import Session

from app.events import SportsEvent
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
