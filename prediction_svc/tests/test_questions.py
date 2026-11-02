import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.ingest import store_event
from app.main import create_app
from app.models import Match, MatchStatus
from tests.tokens import bearer


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
    app.state.session_factory = factory
    return TestClient(app)


def seed_match(api: TestClient, external_id: str = "15") -> None:
    session = api.app.state.session_factory()
    session.add(
        Match(
            external_id=external_id,
            sport="football",
            home_id="1",
            home_name="North",
            away_id="2",
            away_name="South",
            starts_at=datetime(2026, 10, 12, 18, 0, tzinfo=timezone.utc),
            status=MatchStatus.scheduled,
            version=1,
        )
    )
    session.commit()
    session.close()


def test_admin_adds_questions_and_users_filter_them() -> None:
    api = client()
    match_body = {"title": "North победит?", "kind": "match", "match_external_id": "15"}
    event_body = {"title": "Перейдёт ли драфт?", "kind": "event"}

    assert api.post("/questions", json=event_body).status_code == 401
    assert api.post("/questions", headers=bearer("user-1"), json=event_body).status_code == 403
    assert api.post("/questions", headers=bearer("admin"), json={"title": "Без матча", "kind": "match"}).status_code == 422
    assert api.post("/questions", headers=bearer("admin"), json=match_body).status_code == 404

    seed_match(api)
    match = api.post("/questions", headers=bearer("admin"), json=match_body)
    event = api.post("/questions", headers=bearer("admin"), json=event_body)
    assert match.status_code == 201
    assert event.status_code == 201
    assert match.json()["yes_share"] is None
    assert match.json()["home_name"] == "North"
    assert match.json()["away_name"] == "South"
    assert match.json()["match_status"] == "scheduled"
    assert match.json()["starts_at"].startswith("2026-10-12T18:00:00")
    assert event.json()["home_name"] is None

    matches = api.get("/questions", params={"kind": "match"}).json()
    events = api.get("/questions", params={"kind": "event"}).json()
    assert [item["title"] for item in matches] == ["North победит?"]
    assert [item["title"] for item in events] == ["Перейдёт ли драфт?"]


def test_votes_move_the_yes_share_over_time() -> None:
    api = client()
    created = api.post(
        "/questions",
        headers=bearer("admin"),
        json={"title": "Перейдёт ли драфт?", "kind": "event"},
    )
    question_id = created.json()["id"]

    first = api.post(f"/questions/{question_id}/votes", headers=bearer("user-1"), json={"choice": "yes"})
    again = api.post(f"/questions/{question_id}/votes", headers=bearer("user-1"), json={"choice": "yes"})
    second = api.post(f"/questions/{question_id}/votes", headers=bearer("user-2"), json={"choice": "no"})
    changed = api.post(f"/questions/{question_id}/votes", headers=bearer("user-1"), json={"choice": "no"})
    assert first.status_code == 200
    assert again.json()["yes"] == 1
    assert second.json()["yes_share"] == 0.5
    assert changed.json()["yes"] == 0
    assert changed.json()["no"] == 2

    chart = api.get(f"/questions/{question_id}/chart").json()
    assert [point["yes_share"] for point in chart["points"]] == [1.0, 0.5, 0.0]
    assert chart["yes_share"] == 0.0


def test_admin_close_rejects_a_new_vote() -> None:
    api = client()
    created = api.post(
        "/questions",
        headers=bearer("admin"),
        json={"title": "Перейдёт ли драфт?", "kind": "event"},
    )
    question_id = created.json()["id"]

    closed = api.post(f"/questions/{question_id}/close", headers=bearer("admin"))
    rejected = api.post(f"/questions/{question_id}/votes", headers=bearer("user-1"), json={"choice": "yes"})

    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"
    assert rejected.status_code == 409
    assert api.get(f"/questions/{question_id}/chart").status_code == 200


def test_finished_match_shows_the_outcome_and_stops_votes() -> None:
    api = client()
    seed_match(api)
    created = api.post(
        "/questions",
        headers=bearer("admin"),
        json={"title": "North победит?", "kind": "match", "match_external_id": "15"},
    )
    question_id = created.json()["id"]
    api.post(f"/questions/{question_id}/votes", headers=bearer("user-1"), json={"choice": "yes"})

    payload = json.loads((Path(__file__).parent / "fixtures" / "sports_finished.json").read_text(encoding="utf-8"))
    session = api.app.state.session_factory()
    assert store_event(session, payload) == "recorded"
    session.close()

    question = api.get("/questions", params={"kind": "match"}).json()[0]
    rejected = api.post(f"/questions/{question_id}/votes", headers=bearer("user-2"), json={"choice": "no"})
    assert question["status"] == "closed"
    assert question["factual_outcome"] == "home"
    assert question["yes"] == 1
    assert "points" not in question
    assert rejected.status_code == 409


def test_cancelled_match_withdraws_the_question() -> None:
    api = client()
    seed_match(api)
    created = api.post(
        "/questions",
        headers=bearer("admin"),
        json={"title": "North победит?", "kind": "match", "match_external_id": "15"},
    )
    payload = json.loads((Path(__file__).parent / "fixtures" / "sports_finished.json").read_text(encoding="utf-8"))
    payload["event_id"] = "8b2e3d4f-9c53-4f70-1e32-2c3d4e5f6071"
    payload["event_type"] = "match.cancelled"
    payload["status"] = "cancelled"
    payload.pop("outcome")

    session = api.app.state.session_factory()
    assert store_event(session, payload) == "recorded"
    session.close()

    question = api.get(f"/questions/{created.json()['id']}/chart")
    listed = api.get("/questions", params={"kind": "match"}).json()[0]
    assert question.status_code == 200
    assert listed["status"] == "withdrawn"
    assert listed["factual_outcome"] is None
