import re
from datetime import UTC, datetime

from app.api.recommendations import get_user_service
from app.db import SessionLocal
from app.demo_data import load_demo, use_demo_profiles
from app.main import app
from app.news.models import News
from app.preview import preview_user


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
    app.dependency_overrides[preview_user] = lambda: "demo"
    news_id = await _insert("Смотровой матч")
    try:
        page = await client.get("/preview", params={"user_id": "demo"})
        assert page.status_code == 200
        assert "Смотровой матч" in page.text
        assert "Рекомендации" in page.text

        article = await client.get(
            f"/preview/news/{news_id}", params={"user_id": "demo"}
        )
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
        return re.search(
            r'<section[^>]*aria-labelledby="recommendations"[^>]*>(.*?)</section>',
            response.text,
            re.DOTALL,
        ).group(1)

    try:
        football = await recommendation_panel("demo-football")
        assert (
            football.index("Кубковый матч")
            < football.index("СКА")
            < football.index("Дерби")
        )
        assert "По интересам" in football
        ids = re.findall(r"/preview/news/(\d+)\?", football)
        api = await client.get(
            "/api/v1/recommendations", headers={"X-User-Id": "demo-football"}
        )
        assert api.status_code == 200
        assert [item["news_id"] for item in api.json()] == list(map(int, ids))

        hockey = await recommendation_panel("demo-hockey")
        assert (
            hockey.index("СКА")
            < hockey.index("Кубковый матч")
            < hockey.index("Объявлено расписание")
        )
        cold_start = await recommendation_panel("demo")
        assert "По интересам" not in cold_start
        assert (
            cold_start.index("СКА")
            < cold_start.index("Кубковый матч")
            < cold_start.index("Дерби")
        )

        article = await client.get(
            f"/preview/news/{ids[0]}", params={"user_id": "demo-football"}
        )
        assert article.status_code == 200
        assert "Кубковый матч" in article.text

        after = await recommendation_panel("demo-football")
        assert after.index("Дерби") < after.index("СКА") < after.index("Кубковый матч")
        assert after.count(">Открыто</span>") == 1
        assert ">Открыто</span>" not in await recommendation_panel("demo-hockey")
    finally:
        app.dependency_overrides.pop(get_user_service)
        del app.state.preview_profiles


async def test_filtered_pagination_preserves_article_return_context(client):
    from html import unescape
    from urllib.parse import parse_qs, urlsplit

    app.dependency_overrides[get_user_service] = lambda: _NoInterests()
    try:
        for index in range(13):
            await _insert(f"League news {index}")
        response = await client.get(
            "/preview", params={"sport_id": "football", "q": "League"}
        )
        assert response.status_code == 200
        next_url = unescape(
            re.search(
                r'<a[^>]*href="([^"]+)"[^>]*rel="next"', response.text, re.DOTALL
            ).group(1)
        )
        second = await client.get(next_url)
        assert second.status_code == 200
        assert "Страница 2 из 2" in second.text
        article_url = unescape(
            re.search(r'href="(/preview/news/[^\"]+)"', second.text).group(1)
        )
        back = parse_qs(urlsplit(article_url).query)["return_to"][0]
        assert parse_qs(urlsplit(back).query)["sport_id"] == ["football"]
        assert parse_qs(urlsplit(back).query)["q"] == ["League"]
        assert parse_qs(urlsplit(back).query)["offset"] == ["12"]
        article = await client.get(article_url)
        assert article.status_code == 200
        assert back.replace("&", "&amp;") in article.text
        empty = await client.get("/preview", params={"q": "<script>alert(1)</script>"})
        assert empty.status_code == 200
        assert "Новости не найдены" in empty.text
        assert "<script>alert(1)</script>" not in empty.text
    finally:
        app.dependency_overrides.clear()


async def test_login_error_returns_page_and_rejects_external_return(client):
    import httpx

    from app.clients.user_service import UserServiceClient

    transport = httpx.MockTransport(lambda request: httpx.Response(401))
    async with httpx.AsyncClient(transport=transport) as http:
        app.dependency_overrides[get_user_service] = lambda: UserServiceClient(
            "http://users", http
        )
        try:
            response = await client.post(
                "/preview/login",
                data={
                    "username": "reader",
                    "password": "incorrect",
                    "return_to": "https://example.org/",
                },
            )
            assert response.status_code == 401
            assert "Проверьте имя пользователя и пароль" in response.text
            assert 'value="reader"' in response.text
            assert "example.org" not in response.text
            assert "incorrect" not in response.text
        finally:
            app.dependency_overrides.clear()


async def test_guest_comment_redirect_does_not_claim_publication(client):
    from urllib.parse import parse_qs, urlsplit

    news_id = await _insert("Article")
    response = await client.post(
        f"/preview/news/{news_id}/comments", data={"body": "Draft", "user_id": "forged"}
    )
    assert response.status_code == 303
    destination = parse_qs(urlsplit(response.headers["location"]).query)["return_to"][0]
    assert "comment=sent" not in destination
    assert urlsplit(destination).path == f"/preview/news/{news_id}"
    assert (await client.get(f"/api/v1/news/{news_id}/comments")).json() == []
