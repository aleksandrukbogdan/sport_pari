from datetime import UTC, datetime
import re

from app.api.recommendations import get_user_service
from app.db import SessionLocal
from app.demo_data import load_demo, use_demo_profiles
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


async def test_demo_preview_ranks_profiles_and_records_an_opening(client):
    async with SessionLocal.begin() as session:
        await load_demo(session)
    use_demo_profiles(app)

    async def recommendation_panel(user_id: str) -> str:
        response = await client.get("/preview", params={"user_id": user_id})
        assert response.status_code == 200
        assert "Черновик о трансфере" not in response.text
        assert "Болельщик футбола" in response.text
        assert "Болельщик хоккея" in response.text
        return response.text.split('<section aria-labelledby="recommendations">')[1].split("</section>")[0]

    try:
        football = await recommendation_panel("demo-football")
        assert football.index("Кубковый матч") < football.index("Дерби") < football.index("СКА")
        assert "По интересам" in football
        ids = re.findall(r'/preview/news/(\d+)\?', football)
        api = await client.get("/api/v1/recommendations", headers={"X-User-Id": "demo-football"})
        assert api.status_code == 200
        assert [item["news_id"] for item in api.json()] == list(map(int, ids))

        hockey = await recommendation_panel("demo-hockey")
        assert hockey.index("СКА") < hockey.index("Объявлено расписание") < hockey.index("Кубковый матч")
        cold_start = await recommendation_panel("demo")
        assert "По интересам" not in cold_start
        assert cold_start.index("СКА") < cold_start.index("Кубковый матч") < cold_start.index("Дерби")

        article = await client.get(f"/preview/news/{ids[0]}", params={"user_id": "demo-football"})
        assert article.status_code == 200
        assert "Кубковый матч" in article.text

        after = await recommendation_panel("demo-football")
        assert after.index("Дерби") < after.index("СКА") < after.index("Кубковый матч")
        assert after.count(">Открыто</span>") == 1
        assert ">Открыто</span>" not in await recommendation_panel("demo-hockey")
    finally:
        app.dependency_overrides.pop(get_user_service)
        del app.state.preview_profiles
