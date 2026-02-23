#!/usr/bin/env python3
"""Bootstrap script for Django ORM stack: create initial admin user."""

from __future__ import annotations

import asyncio
import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.interface.drf.settings")

import django  # noqa: E402

django.setup()

from app.config import get_settings  # noqa: E402
from app.domain.entities.user import User  # noqa: E402
from app.domain.exceptions import DuplicateUsernameError  # noqa: E402
from app.domain.exceptions.base import DomainError  # noqa: E402
from app.domain.repositories import UserRepository  # noqa: E402
from app.domain.value_objects import Username, UserPasswordHash, UserRole  # noqa: E402
from app.infrastructure.db.django_orm.adapters.uow import UoWDjango  # noqa: E402

cfg = get_settings()


def uow_factory() -> UoWDjango:
    """Return UnitOfWork for Django ORM."""
    return UoWDjango()


async def main() -> int:
    """Bootstrap: create an admin user once."""
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
            repo: UserRepository = uow.get_repo(UserRepository)
            await repo.add(user)
    except DuplicateUsernameError:
        print("[dddapitpl_bootstrap] Username already exists")
        sys.exit(0)

    print(f"[dddapitpl_bootstrap] Admin created (id={user.id}, user={user.username})")
    sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
