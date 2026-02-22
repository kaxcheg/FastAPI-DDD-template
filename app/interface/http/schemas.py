from pydantic import BaseModel, Field

from app.config import get_settings
from app.domain.value_objects.constants import (
    RAW_PASSWORD_MAX_LEN,
    RAW_PASSWORD_MIN_LEN,
    USERNAME_MAX_LEN,
    USERNAME_MIN_LEN,
)

cfg = get_settings()


class ErrorResponse(BaseModel):
    detail: str


class Token(BaseModel):
    """OAuth2-compatible token response with refresh token support."""

    access_token: str
    access_token_type: str
    expires_in: int  # Access token lifetime in seconds
    refresh_token: str | None = Field(
        default=None,
        min_length=cfg.REFRESH_TOKEN_LENGTH * 2,
        max_length=cfg.REFRESH_TOKEN_LENGTH * 2,
    )  # Optional (only for API clients)
    refresh_expires_in: int  # Refresh token lifetime in seconds


class RefreshTokenRequest(BaseModel):
    """Request body for refresh endpoint (JSON clients)."""

    refresh_token: str = Field(
        ...,
        min_length=cfg.REFRESH_TOKEN_LENGTH * 2,
        max_length=cfg.REFRESH_TOKEN_LENGTH * 2,
    )


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=USERNAME_MIN_LEN, max_length=USERNAME_MAX_LEN)
    password: str = Field(
        ..., min_length=RAW_PASSWORD_MIN_LEN, max_length=RAW_PASSWORD_MAX_LEN
    )
    role: str


class CreateUserResponse(BaseModel):
    id: str
    username: str = Field(..., min_length=USERNAME_MIN_LEN, max_length=USERNAME_MAX_LEN)
    role: str


class UserResponse(BaseModel):
    id: str
    username: str = Field(..., min_length=USERNAME_MIN_LEN, max_length=USERNAME_MAX_LEN)
    role: str
    is_active: bool


class GetAllUsersResponse(BaseModel):
    users: list[UserResponse]


class GetUserResponse(BaseModel):
    user: UserResponse


class UpdateUserRequest(BaseModel):
    username: str | None = Field(
        default=None, min_length=USERNAME_MIN_LEN, max_length=USERNAME_MAX_LEN
    )
    role: str | None = None


class UpdateUserResponse(BaseModel):
    user: UserResponse
