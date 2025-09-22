from pydantic import BaseModel, Field

from app.domain.value_objects.constants import (
    RAW_PASSWORD_MAX_LEN,
    RAW_PASSWORD_MIN_LEN,
    USERNAME_MAX_LEN,
    USERNAME_MIN_LEN,
)


class ErrorResponse(BaseModel):
    detail: str


class Token(BaseModel):
    access_token: str
    token_type: str


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
