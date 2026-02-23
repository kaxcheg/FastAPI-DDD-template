from __future__ import annotations

from typing import Callable, ClassVar, TypeVar, cast, override

from asgiref.sync import sync_to_async
from django.db import transaction

from app.application.ports.uow import UnitOfWork
from app.domain.repositories import Repository, UserRepository
from app.infrastructure.db.django_orm.adapters.repo import UserRepositoryDjango
from app.infrastructure.db.django_orm.user_session_repo import UserSessionDjangoRepo

R = TypeVar("R", bound=Repository)

type RepoFactory[R: Repository] = Callable[[], R]


class UoWDjango(UnitOfWork):
    """Unit-of-Work adapter for Django async ORM with transaction.atomic().

    Uses sync_to_async(thread_sensitive=True) so that __enter__/__exit__
    of the Atomic context manager always execute in the same thread,
    keeping Django's connection-local transaction state consistent.
    """

    _REGISTRY: ClassVar[dict[type[Repository], RepoFactory[Repository]]] = {
        UserRepository: lambda: UserRepositoryDjango(),
        UserSessionDjangoRepo: lambda: UserSessionDjangoRepo(),
    }

    def __init__(self) -> None:
        """Initialize UoW (no session factory needed, Django manages connections)."""
        self._atomic: transaction.Atomic | None = None

    @override
    async def _open(self) -> None:
        """Begin a new atomic transaction block."""
        self._atomic = transaction.atomic()
        await sync_to_async(self._atomic.__enter__)()

    @override
    async def commit(self) -> None:
        """Commit by cleanly exiting the atomic block."""
        if self._atomic is not None:
            await sync_to_async(self._atomic.__exit__)(None, None, None)
            self._atomic = None

    @override
    async def rollback(self) -> None:
        """Rollback by setting rollback flag and exiting atomic block."""
        if self._atomic is not None:
            await sync_to_async(transaction.set_rollback)(True)
            await sync_to_async(self._atomic.__exit__)(None, None, None)
            self._atomic = None

    @override
    async def _close(self) -> None:
        """Ensure atomic context is cleaned up."""
        pass

    @override
    def get_repo(self, iface: type[R]) -> R:
        """Return repository instance (stateless, Django manages connections).

        Args:
            iface: Repository interface to resolve.

        Returns:
            R: Repository instance.
        """
        try:
            factory = self._REGISTRY[iface]
        except KeyError as e:
            raise KeyError(f"Repository not registered: {iface!r}") from e
        return cast(R, factory())
