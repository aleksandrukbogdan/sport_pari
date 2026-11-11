from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.events import EventType, SportsEvent
from app.models import Match

SCHEDULE_EVENTS = {EventType.scheduled, EventType.updated}


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def upsert_match(session: Session, event: SportsEvent) -> Match | None:
    snapshot = event.match
    match = session.scalar(select(Match).where(Match.external_id == snapshot.id))
    if match is not None and _is_older(match, event):
        return match
    if match is None and event.event_type not in SCHEDULE_EVENTS:
        return None

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
    if snapshot.score is not None:
        match.score_home = snapshot.score.home
        match.score_away = snapshot.score.away
    if snapshot.outcome is not None:
        match.outcome = snapshot.outcome
    match.version = event.version
    match.source_occurred_at = event.occurred_at
    return match


def _is_older(match: Match, event: SportsEvent) -> bool:
    if match.source_occurred_at is None:
        return event.version < match.version
    stored = _utc(match.source_occurred_at)
    incoming = _utc(event.occurred_at)
    if incoming < stored:
        return True
    if incoming == stored and event.version < match.version:
        return True
    return False
