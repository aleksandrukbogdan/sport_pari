from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.api.deps import CurrentUserId, get_user_service
from app.api.news import _card
from app.api.recommendations import Recommendations
from app.clients.user_service import UserInterests, UserServiceClient

router = APIRouter()
Users = Annotated[UserServiceClient, Depends(get_user_service)]


@router.get("/me")
async def me(users: Users, authorization: Annotated[str | None, Header()] = None):
    return await users.profile(authorization)


@router.get("/me/interests", response_model=UserInterests)
async def interests(user_id: CurrentUserId, users: Users):
    result = await users.get_interests(user_id)
    if result is None:
        raise HTTPException(503, "Interests unavailable")
    return result


@router.put("/me/interests", response_model=UserInterests)
async def update_interests(
    payload: UserInterests,
    users: Users,
    authorization: Annotated[str | None, Header()] = None,
):
    response = await users.authorized_request(
        "PUT", "/user/interests", authorization, json=payload.model_dump()
    )
    try:
        return UserInterests.model_validate(response.json())
    except ValueError as error:
        raise HTTPException(502, "Invalid user service interests") from error


@router.get("/me/feed")
async def feed(
    user_id: CurrentUserId,
    service: Recommendations,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    ranked = await service.rank_for_user(user_id, limit, offset)
    result = []
    for item in ranked:
        card = _card(item.news, item.comments_count)
        result.append(
            dict(
                **card.model_dump(),
                recommendation=item.recommendation.model_dump(),
                seen=item.seen,
            )
        )
    return result
