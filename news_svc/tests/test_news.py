from datetime import UTC, datetime, timedelta

from app.db import SessionLocal
from app.news.models import News
from app.seed import seed_if_empty


async def _insert(**overrides) -> int:
    values = {
        "title": "Заголовок",
        "summary": "Короткий лид",
        "body": "Текст материала",
        "sport_id": "football",
        "published_at": datetime.now(UTC),
    }
    values.update(overrides)
    async with SessionLocal() as session:
        row = News(**values)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


async def test_feed_filters_by_sport_and_hides_drafts(client):
    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC) - timedelta(minutes=5)
    await _insert(title="Старый футбол", sport_id="football", published_at=older)
    await _insert(title="Свежий футбол", sport_id="football", published_at=newer)
    await _insert(title="Хоккей", sport_id="hockey", published_at=newer)
    await _insert(title="Черновик", sport_id="football", published_at=None)

    response = await client.get("/api/v1/news", params={"sport_id": "football"})

    assert response.status_code == 200
    titles = [item["title"] for item in response.json()]
    assert titles == ["Свежий футбол", "Старый футбол"]


async def test_missing_article_returns_404(client):
    response = await client.get("/api/v1/news/999")
    assert response.status_code == 404


async def test_draft_is_not_readable(client):
    news_id = await _insert(published_at=None)
    response = await client.get(f"/api/v1/news/{news_id}")
    assert response.status_code == 404


async def test_seed_fills_empty_feed_once(client):
    assert await seed_if_empty() == 3
    assert await seed_if_empty() == 0
    response = await client.get("/api/v1/news")
    assert response.status_code == 200
    assert len(response.json()) == 3
