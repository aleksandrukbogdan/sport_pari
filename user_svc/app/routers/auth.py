from fastapi import APIRouter, HTTPException, status

from app import schemas, security, storage

router = APIRouter()


@router.post("/registration", response_model=schemas.RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.RegistrationRequest) -> schemas.RegistrationResponse:
    if storage.get_user_by_username(payload.username) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="username already registered")
    if storage.get_user_by_email(payload.email) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="email already registered")

    password_hash = security.hash_password(payload.password)
    user = storage.create_user(payload.username, payload.email, password_hash)
    return schemas.RegistrationResponse(username=user.username, email=user.email, is_verified=user.is_verified)
