from pydantic import BaseModel

from app.config import settings


class UserInterests(BaseModel):
    sport_ids: list[str]
    team_ids: list[str]


class UserServiceClient:
    """Интересы профиля для холодного старта.

    GET {base_url}/users/{user_id}/interests
    JSON: {"sport_ids": [...], "team_ids": [...]}.

    Данные принадлежат сервису пользователей. sport_ids должны совпадать
    с news.sport_id из каталога, иначе любимый вид спорта не найдёт материал.
    Если профиль — отдельный деплой от логина, USER_SERVICE_URL указывает на него.
    Сам HTTP-вызов ещё не написан.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or settings.user_service_url).rstrip("/")

    async def get_interests(self, user_id: str) -> UserInterests:
        raise NotImplementedError("UserServiceClient.get_interests")
