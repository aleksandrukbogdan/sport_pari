from fastapi import APIRouter, HTTPException, Query

from app.api.deps import NewsRepo
from app.news.schemas import NewsCard, NewsDetail

router = APIRouter()


def _card(news_row, comments_count: int) -> NewsCard:
    return NewsCard(
        id=news_row.id,
        title=news_row.title,
        summary=news_row.summary,
        sport_id=news_row.sport_id,
        published_at=news_row.published_at,
        comments_count=comments_count,
    )


@router.get("", response_model=list[NewsCard])
async def list_news(
    repo: NewsRepo,
    sport_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[NewsCard]:
    rows = await repo.list_published(sport_id=sport_id, limit=limit, offset=offset)
    return [_card(news, count) for news, count in rows]


@router.get("/{news_id}", response_model=NewsDetail)
async def get_news(news_id: int, repo: NewsRepo) -> NewsDetail:
    row = await repo.get(news_id)
    if row is None:
        raise HTTPException(status_code=404, detail="News not found")
    news, count = row
    card = _card(news, count)
    return NewsDetail(**card.model_dump(), body=news.body)
