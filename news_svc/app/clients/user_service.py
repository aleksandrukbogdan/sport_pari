from typing import Annotated
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    ValidationError,
    field_validator,
)

from app.config import settings


class UserInterests(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sport_ids: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
        ]
    ] = Field(max_length=100)
    team_ids: list[
        Annotated[
            str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
        ]
    ] = Field(max_length=100)

    @field_validator("sport_ids", "team_ids")
    @classmethod
    def unique_ids(cls, values):
        return list(dict.fromkeys(values))


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
        url = f"{self.base_url}/users/{quote(user_id, safe='')}/interests"
        try:
            response = await self._request(url)
            response.raise_for_status()
            return UserInterests.model_validate(response.json())
        except (httpx.HTTPError, ValidationError, ValueError):
            return None

    async def profile(self, authorization: str) -> dict:
        response = await self.authorized_request("GET", "/user", authorization)
        try:
            data = response.json()
        except ValueError as error:
            raise HTTPException(502, "Invalid user service profile") from error
        if (
            not isinstance(data, dict)
            or not isinstance(data.get("id"), str)
            or not data["id"]
        ):
            raise HTTPException(502, "Invalid user service profile")
        return data

    async def login(self, username: str, password: str) -> str:
        try:
            if self._http is not None:
                response = await self._http.post(
                    f"{self.base_url}/login",
                    json={"username": username, "password": password},
                )
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(
                        f"{self.base_url}/login",
                        json={"username": username, "password": password},
                    )
            if response.status_code in (401, 403, 429):
                raise HTTPException(response.status_code, "Login rejected by user_svc")
            response.raise_for_status()
            token = response.json().get("access_token")
            if not isinstance(token, str) or not token:
                raise ValueError("Missing token")
            return token
        except (ValueError, httpx.HTTPError) as error:
            raise HTTPException(503, "User service login unavailable") from error

    async def authorized_request(
        self, method: str, path: str, authorization: str | None, **kwargs
    ):
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(401, "Bearer token required")
        try:
            if self._http is not None:
                response = await self._http.request(
                    method,
                    f"{self.base_url}{path}",
                    headers={"Authorization": authorization},
                    **kwargs,
                )
            else:
                async with httpx.AsyncClient(timeout=3.0) as client:
                    response = await client.request(
                        method,
                        f"{self.base_url}{path}",
                        headers={"Authorization": authorization},
                        **kwargs,
                    )
            if response.status_code in (401, 403, 404, 409, 422):
                raise HTTPException(
                    response.status_code, "User service rejected the request"
                )
            response.raise_for_status()
            return response
        except httpx.HTTPError as error:
            raise HTTPException(503, "User service unavailable") from error

    async def _request(self, url: str) -> httpx.Response:
        if self._http is not None:
            return await self._http.get(url)
        async with httpx.AsyncClient(timeout=2.0) as client:
            return await client.get(url)
