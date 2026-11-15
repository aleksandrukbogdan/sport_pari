import base64
import json


def bearer(subject: str, expires_at: int | None = None, username: str | None = None) -> dict[str, str]:
    payload: dict[str, str | int] = {"sub": subject}
    if expires_at is not None:
        payload["exp"] = expires_at
    if username is not None:
        payload["preferred_username"] = username
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return {"Authorization": f"Bearer e30.{body}.sig"}
