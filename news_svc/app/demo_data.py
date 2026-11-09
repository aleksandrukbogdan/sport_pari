from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.recommendations import get_user_service
from app.clients.user_service import UserInterests
from app.news.models import News
from app.recommendations.models import NewsView

_PROFILES = {
    "demo": ("Без интересов", []),
    "demo-football": ("Болельщик футбола", ["football"]),
    "demo-hockey": ("Болельщик хоккея", ["hockey"]),
}

# Title, summary, sport, publication age in hours, and ages of individual views.
_ARTICLES = (
    ("Кубковый матч решил поздний гол", "Один просмотр час назад.", "football", 97, (1,)),
    ("Дерби закончилось вничью", "Два просмотра 72 часа назад.", "football", 96, (72, 72)),
    ("СКА вырвал победу в овертайме", "Три просмотра за последние два часа.", "hockey", 12, (1, 2, 2)),
    ("Объявлено расписание плей-офф", "Свежая новость без просмотров.", "hockey", 6, ()),
    ("Медведев вышел в четвертьфинал", "Самая новая публикация без просмотров.", "tennis", 2, ()),
    ("Черновик о трансфере", "Редакция ещё проверяет информацию.", "football", None, ()),
)


class _DemoUserService:
    async def get_interests(self, user_id: str) -> UserInterests | None:
        profile = _PROFILES.get(user_id)
        if profile is None:
            return None
        return UserInterests(sport_ids=profile[1], team_ids=[])


def use_demo_profiles(app: FastAPI) -> None:
    app.dependency_overrides[get_user_service] = _DemoUserService
    app.state.preview_profiles = {user_id: label for user_id, (label, _) in _PROFILES.items()}


async def load_demo(session: AsyncSession) -> None:
    now = datetime.now(UTC)
    for title, summary, sport, published_hours, view_hours in _ARTICLES:
        article = News(
            title=title,
            summary=summary,
            body=f"Вымышленная новость для проверки рекомендаций. {summary}",
            sport_id=sport,
            published_at=None if published_hours is None else now - timedelta(hours=published_hours),
        )
        session.add(article)
        await session.flush()
        session.add_all(
            NewsView(user_id=f"demo-reader-{index}", news_id=article.id, created_at=now - timedelta(hours=age))
            for index, age in enumerate(view_hours, start=1)
        )
