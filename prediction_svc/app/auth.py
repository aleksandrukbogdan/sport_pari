import base64
import json
import time


def subject_from_bearer(token: str) -> str:
    parts = token.split(".")
    if len(parts) != 3 or not all(parts):
        raise ValueError("bearer token must be a jwt")
    padding = "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + padding))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("bearer token payload is not json") from exc
    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("bearer token has no sub")
    expires_at = payload.get("exp")
    if isinstance(expires_at, (int, float)) and expires_at < time.time():
        raise ValueError("bearer token expired")
    return subject
