from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator


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


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=1)
    email: EmailStr | None = None


class DeleteUserResponse(BaseModel):
    status: str
    scheduled_deletion_at: datetime | None = None


InterestId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]


class UserInterests(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sport_ids: list[InterestId] = Field(max_length=100)
    team_ids: list[InterestId] = Field(max_length=100)

    @field_validator("sport_ids", "team_ids")
    @classmethod
    def unique_ids(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))
