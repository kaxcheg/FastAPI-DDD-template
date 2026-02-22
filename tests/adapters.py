from typing import TypeVar, Callable, ClassVar
from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.entities.user.repo import Repository, UserRepository
from app.domain.value_objects import UserId, UserPasswordHash, UserRawPassword, UserRole, Username

from app.domain.value_objects.constants import HASH_LEN
from app.application.dto.base import DTO
from app.application.dto import AuthResponseDTO, CreateUserOutputDTO, GetAllUsersOutputDTO, GetUserOutputDTO, UpdateUserOutputDTO
from app.application.ports.presenters import Presenter, AuthPresenter
from app.application.ports.uow import UnitOfWork
from app.application.ports import AuthService, PasswordVerifier, PasswordHasher, IdGenerator
from app.application.exceptions import DuplicateUserError, NotAuthenticatedError

@dataclass
class TestUser:
    """Test user data structure."""
    id: str
    username: str
    raw_password: str
    password_hash: str
    role: str

class FakePasswordVerifier(PasswordVerifier):
    """Fake password verifier that compares hash with raw for testing."""
    
    def __init__(self, initial_users: list[TestUser]) -> None:
        self.hash_to_raw = {}
        self.hash_to_raw = {
            UserPasswordHash(user.password_hash.encode()): UserRawPassword(user.raw_password) 
            for user in initial_users
        }
    
    def verify(self, raw_password: UserRawPassword, hashed_password: UserPasswordHash) -> bool:
        """Verify password by comparing with known hash-to-raw mapping."""
        expected_raw = self.hash_to_raw.get(hashed_password)
        return expected_raw == raw_password if expected_raw else False


class FakeAuthenticationPresenter(Presenter[AuthResponseDTO]):
    """Test presenter implementation."""

class FakeAuthorizationPresenter(AuthPresenter[DTO]):
    """Test presenter implementation."""    

class FakeCreateUserPresenter(AuthPresenter[CreateUserOutputDTO]):
    """Test Auth presenter implementation."""

class FakeGetAllUsersPresenter(AuthPresenter[GetAllUsersOutputDTO]):
    """Test presenter for GetAllUsers use case."""

class FakeGetUserPresenter(AuthPresenter[GetUserOutputDTO]):
    """Test presenter for GetUser use case."""

class FakeUpdateUserPresenter(AuthPresenter[UpdateUserOutputDTO]):
    """Test presenter for UpdateUser use case."""


class InMemoryUserRepository(UserRepository):
    """In-memory implementation of UserRepository."""
    
    def __init__(self, initial_users:list[TestUser]) -> None:
        self.users_by_id:dict[UserId,User] = {}
        self.users_by_username:dict[Username,User] = {}

        for user in initial_users:
            user_instance = User.from_storage(
                id=UserId.from_str(user.id),
                username=Username(user.username),
                password_hash=UserPasswordHash(user.password_hash.encode()),
                role=UserRole(user.role)
            )
            self.users_by_id[UserId.from_str(user.id)] = user_instance
            self.users_by_username[Username(user.username)] = user_instance
    
    async def get_by_id(self, user_id: UserId) -> User | None:
        """Get user by ID."""
        return self.users_by_id.get(user_id)
    
    async def get_by_username(self, username: Username) -> User | None:
        """Get user by username."""
        return self.users_by_username.get(username)

    async def add(self, user: User) -> None:
        """Save or update user."""
        if user.id in self.users_by_id or user.username in self.users_by_username:
            raise DuplicateUserError
        self.users_by_id[user.id] = user
        self.users_by_username[user.username] = user

    async def update(self, user: User) -> None:
        """Update user in memory store."""
        old_user = self.users_by_id.get(user.id)
        if old_user is None:
            raise ValueError(f"User {user.id} not found")
        existing = self.users_by_username.get(user.username)
        if existing is not None and existing.id != user.id:
            raise DuplicateUserError(f"Username {user.username} already exists")
        if old_user.username in self.users_by_username:
            del self.users_by_username[old_user.username]
        self.users_by_id[user.id] = user
        self.users_by_username[user.username] = user

    async def get_all(self) -> list[User]:
        """Get all users."""
        return list(self.users_by_id.values())
        
        
R = TypeVar("R", bound=Repository)
type RepoFactory[R: Repository] = Callable


class FakeUoW(UnitOfWork):
    """Unit-of-Work adapter for SQLite testing."""

    _REGISTRY: ClassVar[dict[type[Repository], RepoFactory]] = {
        UserRepository: InMemoryUserRepository,
    }

    def __init__(self, initial_users: list[TestUser]):
        self.initial_users = initial_users
        self._repos: dict[type[Repository], Repository] = {}

    async def _open(self) -> None:
        """Begin a new transactional session."""
        pass

    async def commit(self) -> None:
        """Commit active transaction."""
        pass

    async def rollback(self) -> None:
        """Rollback active transaction."""
        pass

    async def _close(self) -> None:
        """Close session safely."""
        pass

    def get_repo(self, iface: type[R]) -> R:
        # Reuse existing repo instance to persist data between UoW sessions
        if iface not in self._repos:
            repo_class = self._REGISTRY[iface]
            self._repos[iface] = repo_class(self.initial_users)
        from typing import cast
        return cast(R, self._repos[iface])


class FakeAuthService(AuthService):
    """Test authentication service implementation."""
    
    def __init__(self, is_user_found: bool, user_role:UserRole=UserRole.ADMIN):
        self.user_role = user_role
        self.is_user_found = is_user_found

    async def current_user(self) -> User:
        """Get current authenticated user."""
        if not self.is_user_found:
            raise NotAuthenticatedError("No authenticated user")
        
        user_stub = User.from_storage(
                id=UserId.new(),
                username=Username("stub_user"),
                password_hash=UserPasswordHash(("x"*HASH_LEN).encode()),
                role=UserRole.USER if self.user_role is UserRole.USER else UserRole.ADMIN
            )

        return user_stub

class FakePasswordHasher(PasswordHasher):
    """Test password hasher implementation."""
    
    def __init__(self, hash_prefix: str = "hashed_"):
        self.hash_prefix = hash_prefix
        
    def hash(self, raw_password: UserRawPassword) -> UserPasswordHash:
        """Create a fake hash from raw password."""

        fake_hash = (self.hash_prefix + raw_password.value)[:HASH_LEN]
        fake_hash = fake_hash.ljust(HASH_LEN, 'x')
        return UserPasswordHash(fake_hash.encode())
    
class FakeIdGenerator(IdGenerator):
    """Test ID generator implementation."""
    
    def new(self) -> UserId:
        """Generate new unique ID."""
        return UserId.new()


