from dataclasses import dataclass

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
