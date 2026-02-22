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


@dataclass(slots=True, frozen=True)
class GetAllUsersInputDTO(DTO): ...


@dataclass(slots=True, frozen=True)
class UserDTO(DTO):
    id: str
    username: str
    role: str
    is_active: bool


@dataclass(slots=True, frozen=True)
class GetAllUsersOutputDTO(DTO):
    users: list[UserDTO]


@dataclass(slots=True, frozen=True)
class GetUserInputDTO(DTO):
    user_id: str


@dataclass(slots=True, frozen=True)
class GetUserOutputDTO(DTO):
    user: UserDTO


@dataclass(slots=True, frozen=True)
class UpdateUserInputDTO(DTO):
    user_id: str
    username: str | None = None
    role: str | None = None


@dataclass(slots=True, frozen=True)
class UpdateUserOutputDTO(DTO):
    user: UserDTO
