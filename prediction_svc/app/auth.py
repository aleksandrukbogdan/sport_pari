import base64
import json
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenIdentity:
    sub: str
    preferred_username: str | None


def identity_from_bearer(token: str) -> TokenIdentity:
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
    username = payload.get("preferred_username")
    if not isinstance(username, str) or not username.strip():
        username = None
    return TokenIdentity(subject, None if username is None else username.strip())


def subject_from_bearer(token: str) -> str:
    return identity_from_bearer(token).sub


def is_admin(identity: TokenIdentity, admin_user_ids: str) -> bool:
    admins = {item.strip() for item in admin_user_ids.split(",") if item.strip()}
    names = {identity.sub}
    if identity.preferred_username:
        names.add(identity.preferred_username)
    return not names.isdisjoint(admins)
