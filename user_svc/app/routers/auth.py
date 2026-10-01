from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import schemas, security, storage

router = APIRouter()

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_username(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    username = storage.resolve_session(credentials.credentials)
    if username is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")

    return username


@router.post("/registration", response_model=schemas.RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.RegistrationRequest) -> schemas.RegistrationResponse:
    if storage.get_user_by_username(payload.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="username already registered")
    if storage.get_user_by_email(payload.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email already registered")

    password_hash = security.hash_password(payload.password)
    user = storage.create_user(payload.username, payload.email, password_hash)
    return schemas.RegistrationResponse(username=user.username, email=user.email, is_verified=user.is_verified)


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest) -> schemas.LoginResponse:
    user = storage.get_user_by_username(payload.username)
    if user is None or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")

    token = security.generate_token()
    storage.create_session(token, user.username)
    return schemas.LoginResponse(access_token=token)


@router.post("/change-password", response_model=schemas.StatusResponse)
def change_password(
    payload: schemas.ChangePasswordRequest,
    username: str = Depends(get_current_username),
) -> schemas.StatusResponse:
    user = storage.get_user_by_username(username)
    if user is None or not security.verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="incorrect current password")

    storage.update_password_hash(username, security.hash_password(payload.new_password))
    return schemas.StatusResponse(status="ok")


@router.post("/reset-password", response_model=schemas.StatusResponse)
def reset_password(payload: schemas.ResetPasswordRequest) -> schemas.StatusResponse:
    user = storage.get_user_by_username_or_email(payload.username_or_email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")

    storage.update_password_hash(user.username, security.hash_password(payload.new_password))
    return schemas.StatusResponse(status="ok")
