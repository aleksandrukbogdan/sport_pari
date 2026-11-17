from datetime import UTC
from pathlib import Path

from fastapi.templating import Jinja2Templates

ROOT = Path(__file__).parent
templates = Jinja2Templates(directory=ROOT / "templates")
SPORTS = {
    "football": "Футбол",
    "basketball": "Баскетбол",
    "hockey": "Хоккей",
    "tennis": "Теннис",
    "formula1": "Формула-1",
    "rugby": "Регби",
    "cricket": "Крикет",
    "athletics": "Лёгкая атлетика",
    "golf": "Гольф",
    "cycling": "Велоспорт",
    "boxing": "Бокс",
    "baseball": "Бейсбол",
}


def date_label(value):
    if value is None:
        return "Дата не указана"
    return (
        value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    ).strftime("%d.%m.%Y · %H:%M UTC")


def date_iso(value):
    if value is None:
        return ""
    return (value.replace(tzinfo=UTC) if value.tzinfo is None else value).isoformat()


templates.env.globals.update(
    sport_label=lambda value: SPORTS.get(value, value),
    date_label=date_label,
    date_iso=date_iso,
)
