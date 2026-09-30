from dataclasses import dataclass


@dataclass
class UserRecord:
    username: str
    email: str
    password_hash: str
    is_verified: bool = False


_users: dict[str, UserRecord] = {}
_sessions: dict[str, str] = {}


def get_user_by_username(username: str) -> UserRecord | None:
    return _users.get(username)


def get_user_by_email(email: str) -> UserRecord | None:
    for user in _users.values():
        if user.email == email:
            return user
    return None


def get_user_by_username_or_email(value: str) -> UserRecord | None:
    return get_user_by_username(value) or get_user_by_email(value)


def create_user(username: str, email: str, password_hash: str) -> UserRecord:
    user = UserRecord(username=username, email=email, password_hash=password_hash)
    _users[username] = user
    return user


def update_password_hash(username: str, password_hash: str) -> None:
    _users[username].password_hash = password_hash


def set_verified(username: str) -> None:
    _users[username].is_verified = True


def create_session(token: str, username: str) -> None:
    _sessions[token] = username


def resolve_session(token: str) -> str | None:
    return _sessions.get(token)


def reset_state() -> None:
    _users.clear()
    _sessions.clear()
