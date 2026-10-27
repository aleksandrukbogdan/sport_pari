from datetime import UTC, datetime

from app.api.recommendations import get_user_service
from app.clients.user_service import UserInterests
from app.db import SessionLocal
from app.main import app
from app.news.models import News
from app.recommendations.models import NewsView


async def _insert(title: str, sport_id: str, *, published: bool = True) -> int:
    published_at = datetime.now(UTC) if published else None
    async with SessionLocal() as session:
        row = News(
            title=title,
            summary="Лид",
            body="Текст",
            sport_id=sport_id,
            published_at=published_at,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


class _Users:
    def __init__(self, interests: UserInterests | None) -> None:
        self._interests = interests

    async def get_interests(self, user_id: str) -> UserInterests | None:
        return self._interests


def _use_interests(interests: UserInterests | None) -> None:
    app.dependency_overrides[get_user_service] = lambda: _Users(interests)


async def test_recommendations_are_published_news(client):
    _use_interests(None)
    older = await _insert("Старый футбол", "football")
    newer = await _insert("Свежий хоккей", "hockey")
    await _insert("Черновик", "football", published=False)
    try:
        response = await client.get(
            "/api/v1/recommendations",
            headers={"X-User-Id": "user-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert [item["news_id"] for item in payload] == [newer, older]
    assert {item["reason"] for item in payload} == {"popularity"}


async def test_matching_sport_is_lifted_when_profile_answers(client):
    _use_interests(UserInterests(sport_ids=["football"], team_ids=[]))
    football = await _insert("Футбол", "football")
    hockey = await _insert("Хоккей", "hockey")
    try:
        response = await client.get(
            "/api/v1/recommendations",
            headers={"X-User-Id": "user-1"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["news_id"] == football
    assert payload[0]["reason"] == "sport"
    assert payload[1]["news_id"] == hockey
    assert payload[1]["reason"] == "popularity"


async def test_opened_article_sinks_but_stays_in_the_list(client):
    _use_interests(None)
    first = await _insert("Первый", "football")
    second = await _insert("Второй", "hockey")
    opened = await client.post(
        "/api/v1/recommendations/views",
        headers={"X-User-Id": "user-1"},
        json={"news_id": second},
    )
    assert opened.status_code == 201
    try:
        response = await client.get(
            "/api/v1/recommendations",
            headers={"X-User-Id": "user-1"},
        )
    finally:
        app.dependency_overrides.clear()

    ids = [item["news_id"] for item in response.json()]
    assert ids == [first, second]


async def test_view_of_missing_news_returns_404(client):
    response = await client.post(
        "/api/v1/recommendations/views",
        headers={"X-User-Id": "user-1"},
        json={"news_id": 999},
    )
    assert response.status_code == 404


async def test_comment_is_not_copied_into_views(client):
    news_id = await _insert("Матч", "football")
    created = await client.post(
        f"/api/v1/news/{news_id}/comments",
        headers={"X-User-Id": "user-1"},
        json={"body": "Жду игру"},
    )
    assert created.status_code == 201
    async with SessionLocal() as session:
        views = await session.scalars(select_views())
        assert list(views) == []


def select_views():
    from sqlalchemy import select

    return select(NewsView)
