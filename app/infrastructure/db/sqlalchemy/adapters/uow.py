from __future__ import annotations

from typing import Callable, ClassVar, TypeVar, override

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
)

from app.application.ports.uow import UnitOfWork
from app.domain.entities.base import Repository
from app.domain.entities.user.repo import UserRepository
from app.infrastructure.db.sqlalchemy.adapters.repo import UserRepositorySQL
from app.infrastructure.db.sqlalchemy.user_session_repo import UserSessionORMRepo

type RepoFactory[R: Repository] = Callable[[AsyncSession], R]


R = TypeVar("R", bound=Repository)


class UoWSQL(UnitOfWork):
    """Unit-of-Work adapter for async SQLAlchemy."""

    _REGISTRY: ClassVar[dict[type[Repository], RepoFactory[Repository]]] = {
        UserRepository: lambda s: UserRepositorySQL(s),
        UserSessionORMRepo: lambda s: UserSessionORMRepo(s),
    }

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initialize with session factory."""
        self._sf = session_factory
        self._session: AsyncSession | None = None
        self._txn: AsyncSessionTransaction | None = None

    @override
    async def _open(self) -> None:
        """Begin a new transactional session."""
        self._session = self._sf()
        self._txn = await self._session.begin()

    @override
    async def commit(self) -> None:
        """Commit active transaction."""
        assert self._txn is not None, "No transaction started"
        await self._txn.commit()

    @override
    async def rollback(self) -> None:
        """Rollback active transaction."""
        assert self._txn is not None, "No transaction started"
        await self._txn.rollback()

    @override
    async def _close(self) -> None:
        """Close session safely."""
        if self._session is not None:
            await self._session.close()

    @override
    def get_repo(self, iface: type[R]) -> R:
        """Return repository instance bound to current session.

        Args:
            iface: Repository interface to resolve.

        Returns:
            R: Repository bound to the active session.
        """
        assert self._session is not None, "No session opened"
        try:
            factory = self._REGISTRY[iface]
        except KeyError as e:
            raise KeyError(f"Repository not registered: {iface!r}") from e

        repo = factory(self._session)

        # Safe cast: registry binds factory to iface type.
        from typing import cast

        return cast(R, repo)
