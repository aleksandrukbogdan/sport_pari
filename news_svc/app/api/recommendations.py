from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import CurrentUserId, NewsRepo, SessionDep
from app.clients.user_service import UserServiceClient
from app.recommendations.models import NewsView
from app.recommendations.repository import PostgresViewRepository
from app.recommendations.schemas import Recommendation, ViewCreate
from app.recommendations.service import RecommendationService

router = APIRouter()


def get_view_repository(session: SessionDep) -> PostgresViewRepository:
    return PostgresViewRepository(session)


def get_user_service() -> UserServiceClient:
    return UserServiceClient()


def get_recommendation_service(
    news: NewsRepo,
    views: Annotated[PostgresViewRepository, Depends(get_view_repository)],
    users: Annotated[UserServiceClient, Depends(get_user_service)],
) -> RecommendationService:
    return RecommendationService(news, views, users)


ViewRepo = Annotated[PostgresViewRepository, Depends(get_view_repository)]
Recommendations = Annotated[RecommendationService, Depends(get_recommendation_service)]


@router.get("", response_model=list[Recommendation])
async def recommend(
    user_id: CurrentUserId,
    service: Recommendations,
    limit: int = Query(default=10, ge=1, le=50),
) -> list[Recommendation]:
    return await service.for_user(user_id, limit)


@router.post("/views", status_code=201)
async def record_view(
    payload: ViewCreate,
    user_id: CurrentUserId,
    views: ViewRepo,
) -> dict[str, str]:
    await views.add(NewsView(user_id=user_id, news_id=payload.news_id))
    return {"status": "accepted"}
