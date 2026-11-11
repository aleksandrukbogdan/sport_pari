import json
from urllib.request import urlopen

from sqlalchemy.orm import Session

from app.ingest import store_event


def fetch_sports_events(url: str) -> list[dict]:
    with urlopen(url, timeout=5) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError("sports events response must be a list")
    return payload


def pull_sports_events(session: Session, events: list[dict]) -> dict[str, int]:
    counts = {"accepted": 0, "recorded": 0, "skipped": 0}
    for event in events:
        result = store_event(session, event)
        counts[result] = counts.get(result, 0) + 1
    return counts
