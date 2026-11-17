from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import Query

from app.api.deps import NewsRepo
from app.news.schemas import NewsCard
from app.news.schemas import NewsDetail

router = APIRouter()


def _card(news_row, comments_count: int) -> NewsCard:
    return NewsCard(
        id=news_row.id,
        title=news_row.title,
        summary=news_row.summary,
        sport_id=news_row.sport_id,
        published_at=news_row.published_at,
        comments_count=comments_count,
        team_ids=news_row.team_ids,
        source_url=news_row.source_url,
        source_name=news_row.source_name,
        image_url=news_row.image_url,
    )


@router.get("", response_model=list[NewsCard])
async def list_news(
    repo: NewsRepo,
    sport_id: str | None = None,
    q: str | None = Query(default=None, min_length=1, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[NewsCard]:
    rows = await repo.list_published(sport_id=sport_id, limit=limit, offset=offset, q=q)
    return [_card(news, count) for news, count in rows]


@router.get("/{news_id}", response_model=NewsDetail)
async def get_news(news_id: int, repo: NewsRepo) -> NewsDetail:
    row = await repo.get(news_id)
    if row is None:
        raise HTTPException(status_code=404, detail="News not found")
    news, count = row
    card = _card(news, count)
    return NewsDetail(**card.model_dump(), body=news.body)
