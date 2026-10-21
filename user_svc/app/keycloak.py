import logging
import threading
import time
from dataclasses import dataclass

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class KeycloakUnavailable(Exception):
    pass


class InvalidCredentials(Exception):
    pass


class EmailNotVerified(Exception):
    pass


class PasswordExpired(Exception):
    pass


class AccountLocked(Exception):
    pass


class InvalidRefreshToken(Exception):
    pass


class InvalidUserData(Exception):
    pass


class KeycloakConflict(Exception):
    def __init__(self, field: str) -> None:
        super().__init__(field)
        self.field = field


@dataclass
class TokenUser:
    id: str
    username: str
    session_id: str


@dataclass
class Tokens:
    access_token: str
    expires_in: int
    refresh_token: str
    refresh_expires_in: int


class KeycloakClient:
    def __init__(self, settings: Settings) -> None:
        base = settings.keycloak_url.rstrip("/")
        realm = settings.keycloak_realm
        self._realm_url = f"{base}/realms/{realm}"
        self._admin_url = f"{base}/admin/realms/{realm}"
        self._client_id = settings.keycloak_client_id
        self._client_secret = settings.keycloak_client_secret
        self._http = httpx.Client(timeout=10.0)
        self._admin_token: str | None = None
        self._admin_token_expires_at = 0.0
        self._lock = threading.Lock()

    def close(self) -> None:
        self._http.close()

    def _send(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            return self._http.request(method, url, **kwargs)
        except httpx.HTTPError as exc:
            raise KeycloakUnavailable from exc

    @staticmethod
    def _ensure_ok(response: httpx.Response) -> None:
        if response.is_error:
            raise KeycloakUnavailable(f"keycloak responded with {response.status_code}")

    @staticmethod
    def _json_field(response: httpx.Response, key: str) -> str:
        try:
            value = response.json().get(key, "")
        except (ValueError, AttributeError):
            return ""
        return value if isinstance(value, str) else ""

    def _oidc_request(self, endpoint: str, data: dict[str, str]) -> httpx.Response:
        return self._send(
            "POST",
            f"{self._realm_url}/protocol/openid-connect/{endpoint}",
            data={**data, "client_id": self._client_id, "client_secret": self._client_secret},
        )

    def _token_request(self, data: dict[str, str]) -> httpx.Response:
        return self._oidc_request("token", data)

    def _admin_headers(self) -> dict[str, str]:
        with self._lock:
            if self._admin_token is None or time.monotonic() >= self._admin_token_expires_at:
                response = self._token_request({"grant_type": "client_credentials"})
                self._ensure_ok(response)
                body = response.json()
                self._admin_token = body["access_token"]
                self._admin_token_expires_at = time.monotonic() + body["expires_in"] - 10
            return {"Authorization": f"Bearer {self._admin_token}"}

    def _invalidate_admin_token(self) -> None:
        with self._lock:
            self._admin_token = None

    def _admin_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        response = self._send(method, f"{self._admin_url}{path}", headers=self._admin_headers(), **kwargs)
        if response.status_code == 401:
            self._invalidate_admin_token()
            response = self._send(method, f"{self._admin_url}{path}", headers=self._admin_headers(), **kwargs)
        return response

    @staticmethod
    def _tokens(response: httpx.Response) -> Tokens:
        body = response.json()
        return Tokens(
            access_token=body["access_token"],
            expires_in=body["expires_in"],
            refresh_token=body["refresh_token"],
            refresh_expires_in=body["refresh_expires_in"],
        )

    def login(self, username: str, password: str) -> Tokens:
        response = self._token_request({"grant_type": "password", "username": username, "password": password})
        if response.status_code in (400, 401) and self._json_field(response, "error") == "invalid_grant":
            description = self._json_field(response, "error_description")
            user = self._find_user_by_username(username)
            if description == "Account is not fully set up":
                if user and "VERIFY_EMAIL" in user.get("requiredActions", []):
                    raise EmailNotVerified
                raise PasswordExpired
            if user and self._is_locked(user["id"]):
                raise AccountLocked
            raise InvalidCredentials
        self._ensure_ok(response)
        return self._tokens(response)

    def _find_user_by_username(self, username: str) -> dict | None:
        response = self._admin_request("GET", "/users", params={"username": username, "exact": "true"})
        self._ensure_ok(response)
        users = response.json()
        return users[0] if users else None

    def _is_locked(self, user_id: str) -> bool:
        response = self._admin_request("GET", f"/attack-detection/brute-force/users/{user_id}")
        self._ensure_ok(response)
        return bool(response.json().get("disabled"))

    def refresh(self, refresh_token: str) -> Tokens:
        response = self._token_request({"grant_type": "refresh_token", "refresh_token": refresh_token})
        if response.status_code in (400, 401) and self._json_field(response, "error") == "invalid_grant":
            raise InvalidRefreshToken
        self._ensure_ok(response)
        return self._tokens(response)

    def verify_password(self, username: str, password: str) -> None:
        tokens = self.login(username, password)
        try:
            response = self._oidc_request("logout", {"refresh_token": tokens.refresh_token})
            self._ensure_ok(response)
        except KeycloakUnavailable:
            logger.warning("could not end the password verification session for user %s", username, exc_info=True)

    def logout(self, session_id: str) -> None:
        response = self._admin_request("DELETE", f"/sessions/{session_id}")
        if response.status_code == 404:
            return
        self._ensure_ok(response)

    def introspect(self, token: str) -> TokenUser | None:
        response = self._send(
            "POST",
            f"{self._realm_url}/protocol/openid-connect/token/introspect",
            data={"token": token, "client_id": self._client_id, "client_secret": self._client_secret},
        )
        self._ensure_ok(response)
        body = response.json()
        if not body.get("active"):
            return None
        return TokenUser(id=body["sub"], username=body["preferred_username"], session_id=body["sid"])

    def create_user(self, username: str, email: str, password: str) -> dict:
        response = self._admin_request(
            "POST",
            "/users",
            json={
                "username": username,
                "email": email,
                "enabled": True,
                "emailVerified": False,
                "requiredActions": ["VERIFY_EMAIL"],
                "credentials": [{"type": "password", "value": password, "temporary": False}],
            },
        )
        if response.status_code == 409:
            message = self._json_field(response, "errorMessage").lower()
            raise KeycloakConflict("email" if "email" in message else "username")
        if response.status_code == 400:
            raise InvalidUserData
        self._ensure_ok(response)
        user_id = response.headers["Location"].rsplit("/", 1)[-1]
        created = self.get_user(user_id)
        if created is None:
            raise KeycloakUnavailable("created user was not found")
        return created

    def get_user(self, user_id: str) -> dict | None:
        response = self._admin_request("GET", f"/users/{user_id}")
        if response.status_code == 404:
            return None
        self._ensure_ok(response)
        return response.json()

    def find_user_by_email(self, email: str) -> dict | None:
        response = self._admin_request("GET", "/users", params={"email": email.lower(), "exact": "true"})
        self._ensure_ok(response)
        users = response.json()
        return users[0] if users else None

    def send_actions_email(self, user_id: str, actions: list[str]) -> None:
        response = self._admin_request("PUT", f"/users/{user_id}/execute-actions-email", json=actions)
        self._ensure_ok(response)
