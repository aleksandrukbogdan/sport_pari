from datetime import UTC, datetime, timedelta

import httpx

from app.api.deps import get_user_service
from app.clients.user_service import UserServiceClient
from app.config import settings
from app.main import app


async def test_bearer_identity_is_validated_by_user_service(client, monkeypatch):
    monkeypatch.setattr(settings, "trust_gateway_headers", False)

    def respond(request):
        if request.headers.get("Authorization") != "Bearer valid":
            return httpx.Response(401)
        if request.url.path == "/user":
            return httpx.Response(200, json={"id": "real-user", "username": "reader"})
        return httpx.Response(200, json={"sport_ids": ["football"], "team_ids": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        app.dependency_overrides[get_user_service] = lambda: UserServiceClient(
            "http://user-svc", http
        )
        try:
            assert (
                await client.get(
                    "/api/v1/recommendations", headers={"X-User-Id": "forged"}
                )
            ).status_code == 401
            assert (
                await client.get("/api/v1/me", headers={"Authorization": "Bearer bad"})
            ).status_code == 401
            response = await client.get(
                "/api/v1/me",
                headers={"Authorization": "Bearer valid", "X-User-Id": "forged"},
            )
            assert response.json()["id"] == "real-user"
            response = await client.get(
                "/api/v1/me/feed", headers={"Authorization": "Bearer valid"}
            )
            assert response.status_code == 200
            assert response.json() == []
            response = await client.put(
                "/api/v1/me/interests",
                headers={"Authorization": "Bearer valid"},
                json={"sport_ids": ["football"], "team_ids": []},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.clear()


async def test_editor_publish_search_and_moderate(client, monkeypatch):
    monkeypatch.setattr(settings, "admin_api_key", "test-editor")
    headers = {"X-API-Key": "test-editor"}
    payload = {
        "title": "Cup final",
        "summary": "Match",
        "body": "A match report",
        "sport_id": "football",
        "team_ids": ["club-1"],
    }
    assert (await client.post("/api/v1/editor/news", json=payload)).status_code == 403
    created = await client.post("/api/v1/editor/news", json=payload, headers=headers)
    assert created.status_code == 201
    news_id = created.json()["id"]
    assert (await client.get(f"/api/v1/news/{news_id}")).status_code == 404
    payload["published_at"] = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    await client.put(f"/api/v1/editor/news/{news_id}", json=payload, headers=headers)
    assert (await client.get("/api/v1/news")).json() == []
    assert (
        await client.post(
            f"/api/v1/news/{news_id}/comments",
            headers={"X-User-Id": "reader"},
            json={"body": "Comment"},
        )
    ).status_code == 404
    payload["published_at"] = datetime.now(UTC).isoformat()
    assert (
        await client.put(
            f"/api/v1/editor/news/{news_id}", json=payload, headers=headers
        )
    ).status_code == 200
    assert len((await client.get("/api/v1/news", params={"q": "final"})).json()) == 1
    assert (await client.get("/api/v1/news", params={"q": "%"})).json() == []
    created_comment = await client.post(
        f"/api/v1/news/{news_id}/comments",
        headers={"X-User-Id": "reader"},
        json={"body": "Comment"},
    )
    comment_id = created_comment.json()["id"]
    response = await client.patch(
        f"/api/v1/editor/comments/{comment_id}",
        headers=headers,
        json={"is_hidden": True},
    )
    assert response.status_code == 200
    assert (await client.get(f"/api/v1/news/{news_id}/comments")).json() == []
    assert (await client.get(f"/api/v1/news/{news_id}")).json()["comments_count"] == 0
