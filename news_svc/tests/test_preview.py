from datetime import UTC, datetime

from app.api.recommendations import get_user_service
from app.db import SessionLocal
from app.main import app
from app.news.models import News


async def _insert(title: str) -> int:
    async with SessionLocal() as session:
        row = News(
            title=title,
            summary="Короткий лид",
            body="Полный текст материала",
            sport_id="football",
            published_at=datetime.now(UTC),
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return row.id


async def test_preview_shows_feed_and_article(client):
    app.dependency_overrides[get_user_service] = lambda: _NoInterests()
    news_id = await _insert("Смотровой матч")
    try:
        page = await client.get("/preview", params={"user_id": "demo"})
        assert page.status_code == 200
        assert "Смотровой матч" in page.text
        assert "Рекомендации" in page.text

        article = await client.get(f"/preview/news/{news_id}", params={"user_id": "demo"})
        assert article.status_code == 200
        assert "Полный текст материала" in article.text

        sent = await client.post(
            f"/preview/news/{news_id}/comments",
            data={"user_id": "demo", "body": "Видно в браузере"},
            follow_redirects=True,
        )
        assert sent.status_code == 200
        assert "Видно в браузере" in sent.text
    finally:
        app.dependency_overrides.clear()


class _NoInterests:
    async def get_interests(self, user_id: str):
        return None
