from fastapi import APIRouter
from fastapi import Depends

from app.auth import is_admin
from app.config import get_settings
from app.routers.questions import MeView
from app.routers.questions import require_identity
from app.auth import TokenIdentity

router = APIRouter(tags=["session"])


@router.get("/me", response_model=MeView)
def read_me(identity: TokenIdentity = Depends(require_identity)) -> MeView:
    return MeView(
        sub=identity.sub,
        preferred_username=identity.preferred_username,
        is_admin=is_admin(identity, get_settings().admin_user_ids),
    )
