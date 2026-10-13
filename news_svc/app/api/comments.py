from fastapi import APIRouter, HTTPException, Query

from app.api.deps import CommentRepo, CurrentUserId
from app.comments.models import Comment
from app.comments.schemas import CommentCreate, CommentRead

router = APIRouter()


@router.get("/news/{news_id}/comments", response_model=list[CommentRead])
async def list_comments(
    news_id: int,
    repo: CommentRepo,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> list[CommentRead]:
    comments = await repo.list_for_news(news_id, limit=limit, offset=offset)
    return [CommentRead.model_validate(comment) for comment in comments]


@router.post("/news/{news_id}/comments", response_model=CommentRead, status_code=201)
async def create_comment(
    news_id: int,
    payload: CommentCreate,
    repo: CommentRepo,
    author_id: CurrentUserId,
) -> CommentRead:
    body = payload.body.strip()
    if not body:
        raise HTTPException(status_code=422, detail="body is empty")
    comment = Comment(news_id=news_id, author_id=author_id, body=body)
    saved = await repo.add(comment)
    return CommentRead.model_validate(saved)
