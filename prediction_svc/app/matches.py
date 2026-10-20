from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events import EventType, SportsEvent
from app.models import Match

SCHEDULE_EVENTS = {EventType.scheduled, EventType.updated}


def upsert_match(session: Session, event: SportsEvent) -> Match | None:
    if event.event_type not in SCHEDULE_EVENTS:
        return None

    snapshot = event.match
    match = session.scalar(select(Match).where(Match.external_id == snapshot.id))
    if match is not None and event.version < match.version:
        return match

    if match is None:
        match = Match(external_id=snapshot.id)
        session.add(match)

    match.sport = snapshot.sport
    match.home_id = snapshot.home.id
    match.home_name = snapshot.home.name
    match.away_id = snapshot.away.id
    match.away_name = snapshot.away.name
    match.starts_at = snapshot.starts_at
    match.status = snapshot.status
    match.version = event.version
    return match
