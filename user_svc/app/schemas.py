from pydantic import BaseModel, Field


class RegistrationRequest(BaseModel):
    username: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegistrationResponse(BaseModel):
    username: str
    email: str
    is_verified: bool


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class ResetPasswordRequest(BaseModel):
    username_or_email: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


class SendVerifyRequest(BaseModel):
    username_or_email: str = Field(min_length=1)


class StatusResponse(BaseModel):
    status: str


class VerifyResponse(BaseModel):
    status: str
    is_verified: bool
