from typing import Self

from app.config.logging import setup_logger


from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager
from typing import Type, TypeVar

from app.domain.exceptions.base import DomainError
from app.application.exceptions.base import ApplicationError
from app.domain.entities.user.repo import Repository
R_co = TypeVar("R_co", bound=Repository, covariant=True)

class UnitOfWork(AbstractAsyncContextManager, ABC):
    """Base UoW: обработка commit/rollback «из коробки»."""

    logger = setup_logger(__name__)

    # — инфраструктура должна реализовать эти методы —
    @abstractmethod
    async def _open(self) -> None: ...        # начать транзакцию / сессию
    @abstractmethod
    async def commit(self) -> None: ...
    @abstractmethod
    async def rollback(self) -> None: ...
    @abstractmethod
    async def _close(self) -> None: ...       # закрыть соединение / сессию
    @abstractmethod
    def get_repo(self, iface: Type[R_co]) -> R_co: ...

    # — шаблонный код, который повторять не придётся —
    async def __aenter__(self) -> Self:
        await self._open()
        return self

    async def __aexit__(self, exc_type, *_):
        try:
            if exc_type is None:
                await self.commit()
            else:
                if exc_type not in (DomainError, ApplicationError):
                    self.logger.error({"event": f"Error in infrastructure layer occured while UOW was opened"}, exc_info=True)
                await self.rollback()
        finally:
            await self._close()