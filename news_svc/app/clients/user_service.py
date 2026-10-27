import httpx
from pydantic import BaseModel, ValidationError

from app.config import settings


class UserInterests(BaseModel):
    sport_ids: list[str]
    team_ids: list[str]


class UserServiceClient:
    """Интересы профиля.

    Договорённый контракт, пока у платформы нет другого:
    GET {USER_SERVICE_URL}/users/{user_id}/interests
    JSON: {"sport_ids": [...], "team_ids": [...]}.

    sport_ids — те же id каталога, что news.sport_id.
    Недоступный сервис или битый ответ не роняют ленту: метод возвращает None.
    """

    def __init__(
        self,
        base_url: str | None = None,
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = (base_url or settings.user_service_url).rstrip("/")
        self._http = http

    async def get_interests(self, user_id: str) -> UserInterests | None:
        url = f"{self.base_url}/users/{user_id}/interests"
        try:
            response = await self._request(url)
            response.raise_for_status()
            return UserInterests.model_validate(response.json())
        except (httpx.HTTPError, ValidationError):
            return None

    async def _request(self, url: str) -> httpx.Response:
        if self._http is not None:
            return await self._http.get(url)
        async with httpx.AsyncClient(timeout=2.0) as client:
            return await client.get(url)
