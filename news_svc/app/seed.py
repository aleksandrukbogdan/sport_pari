import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.db import SessionLocal
from app.news.models import News


async def seed_if_empty() -> int:
    """Insert three published articles when the table has no rows.

    Returns how many rows were inserted. A second run inserts nothing.
    """

    async with SessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(News))
        if count:
            await session.rollback()
            return 0
        now = datetime.now(UTC)
        session.add_all(
            [
                News(
                    title="Спартак объявил об усилении атаки",
                    summary="Клуб подписал форварда до конца сезона.",
                    body="Демо-материал футбольной ленты для локальной проверки.",
                    sport_id="football",
                    published_at=now - timedelta(hours=3),
                ),
                News(
                    title="СКА вырвал победу в овертайме",
                    summary="Армейское дерби закончилось на второй минуте овертайма.",
                    body="Демо-материал хоккейной ленты для локальной проверки.",
                    sport_id="hockey",
                    published_at=now - timedelta(hours=1),
                ),
                News(
                    title="Медведев вышел в четвертьфинал",
                    summary="Матч против квалификанта закончился в двух сетах.",
                    body="Демо-материал теннисной ленты для локальной проверки.",
                    sport_id="tennis",
                    published_at=now - timedelta(minutes=20),
                ),
            ]
        )
        await session.commit()
        return 3


def main() -> None:
    inserted = asyncio.run(seed_if_empty())
    print(f"inserted {inserted}")


if __name__ == "__main__":
    main()
