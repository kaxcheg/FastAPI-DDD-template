from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import TypeVar, override

from app.application.exceptions.base import ApplicationError
from app.config.logging import get_logger
from app.domain.entities.user.repo import Repository
from app.domain.exceptions.base import DomainError

R = TypeVar("R", bound=Repository)


class UnitOfWork(AbstractAsyncContextManager, ABC):
    """Unit-of-Work abstraction around a transactional session."""

    logger = get_logger(__name__)

    @abstractmethod
    async def _open(self) -> None: ...
    @abstractmethod
    async def commit(self) -> None: ...
    @abstractmethod
    async def rollback(self) -> None: ...
    @abstractmethod
    async def _close(self) -> None: ...
    @abstractmethod
    def get_repo(self, iface: type[R]) -> R: ...

    """
        R: Repository interface bound to this UoW.
    """

    @override
    async def __aenter__(self) -> UnitOfWork:
        await self._open()
        return self

    @override
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            if exc_type is None:
                await self.commit()
            else:
                if exc_type not in (DomainError, ApplicationError):
                    self.logger.error(
                        {"event": "unhandled infra-layer error in UoW"}, exc_info=True
                    )
                await self.rollback()
        finally:
            await self._close()
