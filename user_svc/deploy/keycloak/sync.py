import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request

APP_ENV = os.environ["APP_ENV"]
VAULT_ADDR = os.environ["VAULT_ADDR"].rstrip("/")
KEYCLOAK_URL = os.environ["KEYCLOAK_URL"].rstrip("/")
REALM = os.environ["KEYCLOAK_REALM"]
INTERVAL = int(os.environ.get("SYNC_INTERVAL", "30"))
EVENTS_INTERVAL = int(os.environ.get("EVENTS_INTERVAL", "10"))
EVENTS_WINDOW = int(os.environ.get("EVENTS_WINDOW", "3600"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("keycloak-sync")

state = {"smtp_version": None, "admin_error_version": None, "admin_credentials": None, "processed_events": {}}


class HttpError(Exception):
    def __init__(self, status):
        super().__init__(f"http {status}")
        self.status = status


def request(method, url, headers=None, body=None, form=None):
    data = None
    request_headers = dict(headers or {})
    if body is not None:
        data = json.dumps(body).encode()
        request_headers["Content-Type"] = "application/json"
    elif form is not None:
        data = urllib.parse.urlencode(form).encode()
        request_headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        raise HttpError(exc.code) from None
    return json.loads(raw) if raw else None


def read_env_file(path):
    values = {}
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if line and "=" in line:
                key, value = line.split("=", 1)
                values[key] = value
    return values


def vault_sealed():
    return request("GET", f"{VAULT_ADDR}/v1/sys/seal-status")["sealed"]


def vault_login():
    credentials = read_env_file(f"/state/approle/{APP_ENV}.env")
    response = request(
        "POST",
        f"{VAULT_ADDR}/v1/auth/approle/login",
        body={"role_id": credentials["VAULT_ROLE_ID"], "secret_id": credentials["VAULT_SECRET_ID"]},
    )
    return response["auth"]["client_token"]


def kv_read(token, name, version=None):
    url = f"{VAULT_ADDR}/v1/secret/data/{APP_ENV}/{name}"
    if version is not None:
        url += f"?version={version}"
    try:
        response = request("GET", url, headers={"X-Vault-Token": token})
    except HttpError as exc:
        if exc.status == 404:
            return None
        raise
    return response["data"]["data"], response["data"]["metadata"]["version"]


def kv_oldest_version(token, name):
    response = request(
        "GET",
        f"{VAULT_ADDR}/v1/secret/metadata/{APP_ENV}/{name}",
        headers={"X-Vault-Token": token},
    )
    return response["data"]["oldest_version"]


def keycloak_admin_token(username, password):
    try:
        response = request(
            "POST",
            f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
            form={"grant_type": "password", "client_id": "admin-cli", "username": username, "password": password},
        )
    except HttpError as exc:
        if exc.status in (400, 401):
            return None
        raise
    return response["access_token"]


def keycloak_headers(token):
    return {"Authorization": f"Bearer {token}"}


def keycloak_set_admin_password(token, username, password):
    query = urllib.parse.urlencode({"username": username, "exact": "true"})
    users = request("GET", f"{KEYCLOAK_URL}/admin/realms/master/users?{query}", headers=keycloak_headers(token))
    request(
        "PUT",
        f"{KEYCLOAK_URL}/admin/realms/master/users/{users[0]['id']}/reset-password",
        headers=keycloak_headers(token),
        body={"type": "password", "value": password, "temporary": False},
    )


def sync_admin(vault_token):
    current = kv_read(vault_token, "keycloak")
    if current is None:
        log.error("secret %s/keycloak not found in vault", APP_ENV)
        return None
    data, version = current
    username = data["admin_username"]
    password = data["admin_password"]

    token = keycloak_admin_token(username, password)
    if token is not None:
        state["admin_error_version"] = None
        state["admin_credentials"] = (username, password)
        return token

    oldest = max(kv_oldest_version(vault_token, "keycloak"), 1)
    for previous_version in range(version - 1, oldest - 1, -1):
        previous = kv_read(vault_token, "keycloak", previous_version)
        if previous is None:
            continue
        token = keycloak_admin_token(username, previous[0].get("admin_password", ""))
        if token is not None:
            keycloak_set_admin_password(token, username, password)
            state["admin_error_version"] = None
            state["admin_credentials"] = (username, password)
            log.info("admin password synchronized from vault version %s", version)
            return keycloak_admin_token(username, password)

    state["admin_credentials"] = None
    if state["admin_error_version"] != version:
        log.error("admin credentials from vault do not match keycloak and no previous version works")
        state["admin_error_version"] = version
    return None


def sync_smtp(vault_token, admin_token):
    current = kv_read(vault_token, "google-smtp")
    if current is None:
        return
    data, version = current
    if state["smtp_version"] == version:
        return
    user = data.get("smtp_user")
    password = data.get("smtp_password")
    state["smtp_version"] = version
    if not user or not password:
        log.error("google-smtp secret must contain smtp_user and smtp_password")
        return
    request(
        "PUT",
        f"{KEYCLOAK_URL}/admin/realms/{REALM}",
        headers=keycloak_headers(admin_token),
        body={
            "smtpServer": {
                "host": "smtp.gmail.com",
                "port": "587",
                "from": user,
                "fromDisplayName": "sport_pari",
                "user": user,
                "password": password,
                "auth": "true",
                "ssl": "false",
                "starttls": "true",
            }
        },
    )
    log.info("smtp settings applied from vault version %s", version)


def end_sessions_started_before(admin_token, user_id, before_ms):
    try:
        sessions = request(
            "GET",
            f"{KEYCLOAK_URL}/admin/realms/{REALM}/users/{user_id}/sessions",
            headers=keycloak_headers(admin_token),
        )
    except HttpError as exc:
        if exc.status == 404:
            return 0
        raise
    ended = 0
    for session in sessions:
        if session["start"] >= before_ms:
            continue
        try:
            request(
                "DELETE",
                f"{KEYCLOAK_URL}/admin/realms/{REALM}/sessions/{session['id']}",
                headers=keycloak_headers(admin_token),
            )
        except HttpError as exc:
            if exc.status != 404:
                raise
        ended += 1
    return ended


def events_cycle():
    credentials = state["admin_credentials"]
    if credentials is None:
        return
    admin_token = keycloak_admin_token(*credentials)
    if admin_token is None:
        return
    since_ms = int((time.time() - EVENTS_WINDOW) * 1000)
    query = urllib.parse.urlencode(
        {
            "type": "UPDATE_PASSWORD",
            "dateFrom": time.strftime("%Y-%m-%d", time.gmtime(since_ms / 1000)),
            "max": 200,
        }
    )
    events = request(
        "GET",
        f"{KEYCLOAK_URL}/admin/realms/{REALM}/events?{query}",
        headers=keycloak_headers(admin_token),
    )
    processed = state["processed_events"]
    for key in [key for key, event_time in processed.items() if event_time < since_ms]:
        del processed[key]
    for event in events:
        user_id = event.get("userId")
        event_time = event["time"]
        key = (user_id, event_time)
        if not user_id or event_time < since_ms or key in processed:
            continue
        ended = end_sessions_started_before(admin_token, user_id, event_time)
        processed[key] = event_time
        log.info("password changed for user %s: ended %s earlier sessions", user_id, ended)


def cycle():
    if vault_sealed():
        log.warning("vault is sealed, skipping cycle")
        return
    vault_token = vault_login()
    admin_token = sync_admin(vault_token)
    if admin_token is None:
        return
    sync_smtp(vault_token, admin_token)


def run(name, action):
    try:
        action()
    except HttpError as exc:
        log.error("%s failed: %s", name, exc)
    except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
        log.error("%s failed: %s: %s", name, type(exc).__name__, exc)


def main():
    log.info(
        "started: env=%s realm=%s sync_interval=%ss events_interval=%ss events_window=%ss",
        APP_ENV,
        REALM,
        INTERVAL,
        EVENTS_INTERVAL,
        EVENTS_WINDOW,
    )
    next_sync = next_events = time.monotonic()
    while True:
        if time.monotonic() >= next_sync:
            run("sync cycle", cycle)
            next_sync = time.monotonic() + INTERVAL
        if time.monotonic() >= next_events:
            run("events cycle", events_cycle)
            next_events = time.monotonic() + EVENTS_INTERVAL
        time.sleep(1)


if __name__ == "__main__":
    main()
