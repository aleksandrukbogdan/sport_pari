import os
import uuid
from datetime import timedelta

from app.sample_data import MATCHES

NAMESPACE = uuid.UUID("6f0c1b2e-7a31-4d5e-9c10-0a1b2c3d4e5f")


def seed_events_enabled() -> bool:
    return os.getenv("SPORTS_SEED_EVENTS", "").strip().lower() in {"1", "true", "yes"}


def event_id(match_id: int, event_type: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{match_id}:{event_type}"))


def build_seed_events() -> list[dict]:
    events = []
    for match in MATCHES:
        events.append(_scheduled(match))
        if match.status == "finished" and match.score is not None:
            events.append(_finished(match))
    return events


def seed_learning_events() -> int:
    if not seed_events_enabled():
        return 0

    from psycopg.errors import UniqueViolation

    from app.database import insert_event
    from app.database import get_connection
    from app.database import read_events

    known = {event["event_id"] for event in read_events()}
    inserted = 0
    for event in build_seed_events():
        if event["event_id"] in known:
            continue
        try:
            with get_connection() as connection:
                insert_event(connection, event)
        except UniqueViolation:
            continue
        known.add(event["event_id"])
        inserted += 1
    return inserted


def _scheduled(match) -> dict:
    return {
        "event_id": event_id(match.match_id, "match.scheduled"),
        "event_type": "match.scheduled",
        "occurred_at": (match.starts_at - timedelta(hours=1)).isoformat(),
        "version": 1,
        "match_id": match.match_id,
        "sport": match.sport,
        "home": match.home.model_dump(),
        "away": match.away.model_dump(),
        "starts_at": match.starts_at.isoformat(),
        "status": "scheduled",
    }


def _finished(match) -> dict:
    home = match.score.home
    away = match.score.away
    if home > away:
        outcome = "home"
    elif home < away:
        outcome = "away"
    else:
        outcome = "draw"
    return {
        "event_id": event_id(match.match_id, "match.finished"),
        "event_type": "match.finished",
        "occurred_at": (match.starts_at + timedelta(hours=2)).isoformat(),
        "version": 1,
        "match_id": match.match_id,
        "sport": match.sport,
        "home": match.home.model_dump(),
        "away": match.away.model_dump(),
        "starts_at": match.starts_at.isoformat(),
        "status": "finished",
        "score": match.score.model_dump(),
        "outcome": outcome,
    }
