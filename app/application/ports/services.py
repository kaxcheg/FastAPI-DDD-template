from typing import TypeVar

from app.domain.entities.user import User
from app.domain.value_objects import UserId, UserPasswordHash, UserRawPassword, UserRole
from app.application.dto import CredentialDTO
from app.domain.entities.user.repo import UserRepository


from typing import Protocol


class PasswordHasher(Protocol):
    def hash(self, raw_password: UserRawPassword) -> UserPasswordHash: ...

R = TypeVar("R", bound=UserRepository, contravariant=True)

class AuthService(Protocol[R]):
    credentials: CredentialDTO
    """Facade over JWT / session store."""
    def __init__(self, credentials: CredentialDTO) -> None:
        self.credentials = credentials

    def ensure_role(self, user_id: UserId, role: UserRole, target_role: UserRole) -> None: ...
    async def current_user(self, repo: R) -> User: ...

class PasswordVerifier(Protocol):
    def verify(self, raw_password: UserRawPassword, hashed_password: UserPasswordHash) -> bool:
        """Return True if raw_password matches the hashed_password."""
        ...