from typing import TypeVar, Type, Final, Callable, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, AsyncSessionTransaction
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import UUID

from app.domain.entities.user import User
from app.domain.entities.base import Repository
from app.domain.entities.user.repo import UserRepository
from app.domain.value_objects import Username, UserId, UserRole, UserPasswordHash
from app.application.ports.uow import UnitOfWork
from app.application.exceptions import DuplicateUserError

from app.infrastructure.db.sqlalchemy.models.user import UserORM


class UserRepositorySQL(UserRepository):
    """SQLAlchemy implementation; maps Domain ⇆ ORM."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_by_id(self, user_id: UserId) -> User|None:
        result = await self._s.get(UserORM, user_id.value)
        if result is None:
            return None
        return User.from_storage(
            id=UserId(result.id),
            username=Username(result.username),
            password_hash=UserPasswordHash(result.password_hash),
            role=UserRole(result.role)
        )

    async def get_by_username(self, username: Username) -> Optional[User]:
        result = await self._s.scalars(select(UserORM).where(UserORM.username == str(username)))
        first = result.first()
        if first is None:
            return None
        return User.from_storage(
            id=UserId(first.id),
            username=Username(first.username),
            password_hash=UserPasswordHash(first.password_hash),
            role=UserRole(first.role)
        )

    async def add(self, user: User) -> None:
        user_orm = UserORM(
            id = user.id.value,
            username = str(user.username),
            password_hash = user.password_hash.value,
            role = str(user.role),
            is_active = user.is_active
        )
        try:
            self._s.add(user_orm)
            await self._s.flush()
        except IntegrityError as e:
            raise DuplicateUserError(f"User {user.username} already exists") from e


R_co = TypeVar("R_co", bound=Repository, covariant=True)
RepoFactory = Callable[[AsyncSession], R_co]

class UoWSQL(UnitOfWork):
    """
    Адаптер Unit-of-Work для async-SQLAlchemy.
    Используется как::

        async with uow_factory() as uow:
            repo = uow.get_repo(UserRepository)
            ...
    """

    _REGISTRY: Final[dict[type[Repository], RepoFactory]] = {
        UserRepository: lambda s: UserRepositorySQL(s),
        
    }

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sf = session_factory
        self._session: AsyncSession | None = None
        self._txn: AsyncSessionTransaction | None = None

    # ── шаблон UnitOfWork (протокол уже дал __aenter__/__aexit__) ────────────
    async def _open(self) -> None:                    # BEGIN;
        self._session = self._sf()
        self._txn = await self._session.begin()

    async def commit(self) -> None:                   # COMMIT;
        await self._txn.commit()            # type: ignore[union-attr]

    async def rollback(self) -> None:                 # ROLLBACK;
        await self._txn.rollback()          # type: ignore[union-attr]

    async def _close(self) -> None:
        await self._session.close()         # type: ignore[union-attr]

    def get_repo(self, iface: Type[R_co]) -> R_co:
        assert self._session is not None, "No session opened"
        factory: RepoFactory = self._REGISTRY[iface] 
        return factory(self._session)


class UUIDv4Generator:
    def new(self) -> UserId:
        return UserId(uuid.uuid4())