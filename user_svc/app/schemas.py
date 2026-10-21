from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class RegistrationRequest(BaseModel):
    username: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=1)


class RegistrationResponse(BaseModel):
    username: str
    email: str
    is_verified: bool
    verification_sent: bool


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600
    refresh_token: str
    refresh_expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    is_verified: bool
    created_at: datetime


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)


class ResetPasswordRequest(BaseModel):
    email: EmailStr


class SendVerifyRequest(BaseModel):
    email: EmailStr


class StatusResponse(BaseModel):
    status: str


class VerifyResponse(BaseModel):
    status: str
    is_verified: bool
