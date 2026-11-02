import time

from fastapi.testclient import TestClient

from app.main import create_app
from tests.tokens import bearer


def test_expired_bearer_is_rejected() -> None:
    api = TestClient(create_app())

    response = api.post(
        "/questions",
        headers=bearer("admin", expires_at=int(time.time()) - 10),
        json={"title": "Перейдёт ли драфт?", "kind": "event"},
    )

    assert response.status_code == 401
