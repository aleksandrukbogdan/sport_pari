from fastapi import APIRouter

from app.api.comments import router as comments_router
from app.api.news import router as news_router

api_router = APIRouter()
api_router.include_router(news_router, prefix="/news", tags=["news"])
api_router.include_router(comments_router, tags=["comments"])
