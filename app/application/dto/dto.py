from dataclasses import dataclass
from typing import Literal

from app.application.dto.base import DTO


@dataclass(slots=True, frozen=True)
class CreateUserInputDTO(DTO):
    username: str
    password: str
    role: str


@dataclass(slots=True, frozen=True)
class CreateUserOutputDTO(DTO):
    id: str
    username: str
    role: str


@dataclass(slots=True, frozen=True)
class AuthRequestDTO(DTO):
    username: str
    raw_password: str


@dataclass(slots=True, frozen=True)
class AuthResponseDTO(DTO):
    user_id: str
    username: str
    role: str


@dataclass(slots=True, frozen=True)
class CredentialDTO(DTO):
    """Flat generic DTO for any kind of authentication artefact."""

    scheme: Literal[
        "bearer",  # Authorization: Bearer <token>
        "cookie",  # сookies
        "basic",  # Basic <base64>
        "apikey",  # X-Api-Key
    ]
    value: str | dict | list
