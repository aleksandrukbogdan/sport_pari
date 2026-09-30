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


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest) -> schemas.LoginResponse:
    user = storage.get_user_by_username(payload.username)
    if user is None or not security.verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")

    token = security.generate_token()
    storage.create_session(token, user.username)
    return schemas.LoginResponse(access_token=token)
