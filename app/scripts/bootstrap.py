#!/usr/bin/env python3

import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.ports.uow import UnitOfWork
from app.config import get_settings
from app.domain.entities.user import User
from app.domain.exceptions import DuplicateUsernameError
from app.domain.exceptions.base import DomainError
from app.domain.repositories import UserRepository
from app.domain.value_objects import Username, UserPasswordHash, UserRole
from app.infrastructure.db.sqlalchemy.adapters.uow import UoWSQL

cfg = get_settings()
engine = create_async_engine(str(cfg.DB_URL), pool_pre_ping=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)


def uow_factory() -> UnitOfWork:
    """Return UnitOfWork bound to the async session."""
    return UoWSQL(async_session)


async def main() -> int:
    """Bootstrap: create an admin user once"""

    username = cfg.BOOTSTRAP_ADMIN
    password_hash = cfg.BOOTSTRAP_ADMIN_PASSWORD_HASH.get_secret_value()

    if not username or not password_hash:
        sys.exit(
            "[dddapitpl_bootstrap] BOOTSTRAP_ADMIN, "
            "BOOTSTRAP_ADMIN_PASSWORD_HASH must be set"
        )

    try:
        user = User.create(
            username=Username(username),
            password_hash=UserPasswordHash(value=password_hash.encode()),
            role=UserRole.ADMIN,
        )
    except (DomainError, ValueError) as e:
        sys.exit(
            f"[dddapitpl_bootstrap] User with provided parameters cannot be created: {e}"
        )

    try:
        async with uow_factory() as uow:
            uow: UnitOfWork
            repo: UserRepository = uow.get_repo(UserRepository)
            await repo.add(user)
    except DuplicateUsernameError:
        print("[dddapitpl_bootstrap] Username already exists")
        sys.exit(0)

    print(f"[dddapitpl_bootstrap] Admin created (id={user.id}, user={user.username})")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
