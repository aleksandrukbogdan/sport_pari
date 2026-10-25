from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import create_app


def client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    return TestClient(app)


def test_admin_adds_questions_and_users_filter_them() -> None:
    api = client()
    match_body = {"title": "North победит?", "kind": "match", "match_external_id": "15"}
    event_body = {"title": "Перейдёт ли драфт?", "kind": "event"}

    assert api.post("/questions", json=event_body).status_code == 401
    assert api.post("/questions", headers={"X-User-Id": "user-1"}, json=event_body).status_code == 403
    assert api.post("/questions", headers={"X-User-Id": "admin"}, json={"title": "Без матча", "kind": "match"}).status_code == 422

    match = api.post("/questions", headers={"X-User-Id": "admin"}, json=match_body)
    event = api.post("/questions", headers={"X-User-Id": "admin"}, json=event_body)
    assert match.status_code == 201
    assert event.status_code == 201
    assert match.json()["yes_share"] is None

    matches = api.get("/questions", params={"kind": "match"}).json()
    events = api.get("/questions", params={"kind": "event"}).json()
    assert [item["title"] for item in matches] == ["North победит?"]
    assert [item["title"] for item in events] == ["Перейдёт ли драфт?"]


def test_votes_move_the_yes_share_over_time() -> None:
    api = client()
    created = api.post(
        "/questions",
        headers={"X-User-Id": "admin"},
        json={"title": "Перейдёт ли драфт?", "kind": "event"},
    )
    question_id = created.json()["id"]

    first = api.post(f"/questions/{question_id}/votes", headers={"X-User-Id": "user-1"}, json={"choice": "yes"})
    again = api.post(f"/questions/{question_id}/votes", headers={"X-User-Id": "user-1"}, json={"choice": "yes"})
    second = api.post(f"/questions/{question_id}/votes", headers={"X-User-Id": "user-2"}, json={"choice": "no"})
    changed = api.post(f"/questions/{question_id}/votes", headers={"X-User-Id": "user-1"}, json={"choice": "no"})
    assert first.status_code == 200
    assert again.json()["yes"] == 1
    assert second.json()["yes_share"] == 0.5
    assert changed.json()["yes"] == 0
    assert changed.json()["no"] == 2

    chart = api.get(f"/questions/{question_id}/chart").json()
    assert [point["yes_share"] for point in chart["points"]] == [1.0, 0.5, 0.0]
    assert chart["yes_share"] == 0.0
