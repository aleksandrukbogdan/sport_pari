import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import keycloak, schemas

logger = logging.getLogger(__name__)

router = APIRouter()

_bearer_scheme = HTTPBearer(auto_error=False)


def get_keycloak(request: Request) -> keycloak.KeycloakClient:
    return request.app.state.keycloak


def _login_response(tokens: keycloak.Tokens) -> schemas.LoginResponse:
    return schemas.LoginResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        refresh_token=tokens.refresh_token,
        refresh_expires_in=tokens.refresh_expires_in,
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> keycloak.TokenUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")

    user = kc.introspect(credentials.credentials)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")

    return user


@router.post("/registration", response_model=schemas.RegistrationResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: schemas.RegistrationRequest,
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.RegistrationResponse:
    try:
        user = kc.create_user(payload.username, payload.email, payload.password)
    except keycloak.KeycloakConflict as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"{exc.field} already registered")
    except keycloak.InvalidUserData:
        raise HTTPException(422, detail="invalid user data")

    verification_sent = True
    try:
        kc.send_actions_email(user["id"], ["VERIFY_EMAIL"])
    except keycloak.KeycloakUnavailable:
        verification_sent = False
        logger.warning("verification email was not sent for user %s", user["id"], exc_info=True)

    return schemas.RegistrationResponse(
        username=user["username"],
        email=user["email"],
        is_verified=bool(user.get("emailVerified", False)),
        verification_sent=verification_sent,
    )


@router.post("/login", response_model=schemas.LoginResponse)
def login(
    payload: schemas.LoginRequest,
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.LoginResponse:
    try:
        tokens = kc.login(payload.username, payload.password)
    except keycloak.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")
    except keycloak.EmailNotVerified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="email not verified")
    except keycloak.PasswordExpired:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="password expired")
    except keycloak.AccountLocked:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="too many failed login attempts")

    return _login_response(tokens)


@router.post("/refresh", response_model=schemas.LoginResponse)
def refresh(
    payload: schemas.RefreshRequest,
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.LoginResponse:
    try:
        tokens = kc.refresh(payload.refresh_token)
    except keycloak.InvalidRefreshToken:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="invalid or expired refresh token")

    return _login_response(tokens)


@router.get("/user", response_model=schemas.UserResponse)
def read_user(
    current_user: keycloak.TokenUser = Depends(get_current_user),
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.UserResponse:
    user = kc.get_user(current_user.id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")

    return schemas.UserResponse(
        id=user["id"],
        username=user["username"],
        email=user.get("email", ""),
        is_verified=bool(user.get("emailVerified", False)),
        created_at=datetime.fromtimestamp(user["createdTimestamp"] / 1000, tz=timezone.utc),
    )


@router.post("/change-password", response_model=schemas.StatusResponse)
def change_password(
    payload: schemas.ChangePasswordRequest,
    current_user: keycloak.TokenUser = Depends(get_current_user),
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.StatusResponse:
    try:
        kc.verify_password(current_user.username, payload.old_password)
    except keycloak.InvalidCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="incorrect current password")
    except keycloak.PasswordExpired:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="password expired")
    except keycloak.AccountLocked:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="too many failed login attempts")

    kc.send_actions_email(current_user.id, ["UPDATE_PASSWORD"])
    return schemas.StatusResponse(status="ok")


@router.post("/logout", response_model=schemas.StatusResponse)
def logout(
    current_user: keycloak.TokenUser = Depends(get_current_user),
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.StatusResponse:
    kc.logout(current_user.session_id)
    return schemas.StatusResponse(status="ok")


@router.post("/reset-password", response_model=schemas.StatusResponse)
def reset_password(
    payload: schemas.ResetPasswordRequest,
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.StatusResponse:
    user = kc.find_user_by_email(payload.email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")

    kc.send_actions_email(user["id"], ["UPDATE_PASSWORD"])
    return schemas.StatusResponse(status="ok")


@router.post("/send-verify", response_model=schemas.VerifyResponse)
def send_verify(
    payload: schemas.SendVerifyRequest,
    kc: keycloak.KeycloakClient = Depends(get_keycloak),
) -> schemas.VerifyResponse:
    user = kc.find_user_by_email(payload.email)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")

    kc.send_actions_email(user["id"], ["VERIFY_EMAIL"])
    return schemas.VerifyResponse(status="ok", is_verified=bool(user.get("emailVerified", False)))
