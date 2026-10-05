from fastapi import APIRouter, Query

from app.api.deps import CurrentUserId
from app.recommendations.models import NewsView
from app.recommendations.repository import PostgresViewRepository
from app.recommendations.schemas import Recommendation, ViewCreate
from app.recommendations.service import RecommendationService

router = APIRouter()


@router.get("", response_model=list[Recommendation])
async def recommend(
    user_id: CurrentUserId,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[Recommendation]:
    return await RecommendationService().for_user(user_id, limit)


@router.post("/views", status_code=201)
async def record_view(payload: ViewCreate, user_id: CurrentUserId) -> dict[str, str]:
    view = NewsView(user_id=user_id, news_id=payload.news_id)
    await PostgresViewRepository().add(view)
    return {"status": "accepted"}
