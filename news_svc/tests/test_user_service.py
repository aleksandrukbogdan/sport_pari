import httpx

from app.clients.user_service import UserServiceClient


async def test_interests_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/users/user-1/interests"
        return httpx.Response(200, json={"sport_ids": ["football"], "team_ids": ["cska"]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = UserServiceClient(base_url="http://user-svc", http=http)
        interests = await client.get_interests("user-1")

    assert interests is not None
    assert interests.sport_ids == ["football"]
    assert interests.team_ids == ["cska"]


async def test_interests_unavailable():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("user service is down", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = UserServiceClient(base_url="http://user-svc", http=http)
        assert await client.get_interests("user-1") is None
