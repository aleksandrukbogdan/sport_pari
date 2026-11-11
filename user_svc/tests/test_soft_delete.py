import os
import uuid
from datetime import datetime, timedelta

import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")
KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://localhost:18080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "sport-pari")
CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "user-svc")
CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "dev-secret-change-me")


def _admin_token() -> str:
    resp = httpx.post(
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_admin_token()}"}


def _find_user_by_username(username: str) -> dict:
    resp = httpx.get(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users",
        params={"username": username, "exact": "true"},
        headers=_admin_headers(),
    )
    resp.raise_for_status()
    users = resp.json()
    assert users, f"user {username} not found in Keycloak"
    return users[0]


def _prepare_user_for_login(user_id: str, new_password: str) -> None:
    resp = httpx.put(
        f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}/users/{user_id}",
        headers=_admin_headers(),
        json={
            "emailVerified": True,
            "requiredActions": [],
            "credentials": [{"type": "password", "value": new_password, "temporary": False}],
        },
    )
    resp.raise_for_status()


def test_soft_delete_user():
    """Register user, get /user 200, DELETE /user, then /user returns 401."""
    username = f"test-{uuid.uuid4().hex[:12]}"
    email = f"{username}@example.com"
    password = "Str0ngPass!1234"

    with httpx.Client(base_url=API_URL, timeout=30) as client:
        # Register
        resp = client.post(
            "/registration",
            json={"username": username, "email": email, "password": password},
        )
        assert resp.status_code == 201, resp.text

        # Prepare user for login (verify email, set a permanent password)
        user = _find_user_by_username(username)
        new_password = f"{password}-final"
        _prepare_user_for_login(user["id"], new_password)

        # Login
        resp = client.post("/login", json={"username": username, "password": new_password})
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # GET /user → 200
        resp = client.get("/user", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["username"] == username.lower()
        assert body["email"] == email.lower()
        assert body["is_verified"] is True

        # DELETE /user → 200 (soft delete)
        resp = client.delete("/user", headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] == "ok"
        assert body["scheduled_deletion_at"] is not None
        scheduled_at = datetime.fromisoformat(body["scheduled_deletion_at"])
        assert scheduled_at > datetime.now(scheduled_at.tzinfo) + timedelta(days=170)

        # Verify user is disabled in Keycloak
        kc_user = _find_user_by_username(username)
        assert kc_user["enabled"] is False
        attrs = kc_user.get("attributes", {})
        assert "deletion_scheduled_at" in attrs

        # GET /user with same token → 401 (token no longer active after soft delete)
        resp = client.get("/user", headers=headers)
        assert resp.status_code == 401, resp.text
