from datetime import UTC, datetime

from app.db import SessionLocal
from app.news.models import News


async def _insert_news(*, published: bool = True) -> int:
    async with SessionLocal() as session:
        row = News(
            title="Матч тура",
            summary="Короткий лид",
            body="Текст материала",
            sport_id="football",
            published_at=datetime.now(UTC) if published else None,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


async def test_comment_without_user_is_rejected(client):
    news_id = await _insert_news()
    response = await client.post(
        f"/api/v1/news/{news_id}/comments",
        json={"body": "Интересный матч"},
    )
    assert response.status_code == 401


async def test_comment_on_missing_news_returns_404(client):
    response = await client.post(
        "/api/v1/news/999/comments",
        headers={"X-User-Id": "user-1"},
        json={"body": "Где этот материал?"},
    )
    assert response.status_code == 404
    listing = await client.get("/api/v1/news/999/comments")
    assert listing.status_code == 404


async def test_comment_increases_count_on_the_card(client):
    news_id = await _insert_news()
    created = await client.post(
        f"/api/v1/news/{news_id}/comments",
        headers={"X-User-Id": "user-1"},
        json={"body": "Жду воскресный матч"},
    )
    assert created.status_code == 201
    assert created.json()["author_id"] == "user-1"

    card = await client.get(f"/api/v1/news/{news_id}")
    assert card.status_code == 200
    assert card.json()["comments_count"] == 1

    thread = await client.get(f"/api/v1/news/{news_id}/comments")
    assert thread.status_code == 200
    assert [item["body"] for item in thread.json()] == ["Жду воскресный матч"]
