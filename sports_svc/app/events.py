from datetime import datetime, timezone
from uuid import uuid4

from app.schemas import Match


def create_event(match: Match, event_type: str):
    event = {
        "event_id": str(uuid4()),  # у каждого события свой номер
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "match_id": match.match_id,
        "sport": match.sport,
        "home": match.home.model_dump(),
        "away": match.away.model_dump(),
        "starts_at": match.starts_at.isoformat(),
        "status": match.status,
    }

    if event_type == "match.started":
        #Фактическое время начала хранится отдельно от планового
        event["started_at"] = event["occurred_at"]

    if event_type in ["match.score_changed", "match.finished", "match.result_corrected"]:
        event["score"] = match.score.model_dump()

    #Победителя определяем только по окончательному результату
    if event_type in ["match.finished", "match.result_corrected"]:
        if match.score.home > match.score.away:
            event["outcome"] = "home"
        elif match.score.home < match.score.away:
            event["outcome"] = "away"
        else:
            event["outcome"] = "draw"

    return event