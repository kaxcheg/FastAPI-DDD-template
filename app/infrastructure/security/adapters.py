from __future__ import annotations

from typing import override

import bcrypt

from app.application.ports.services import PasswordHasher, PasswordVerifier
from app.domain.value_objects import UserPasswordHash, UserRawPassword


class BcryptHasher(PasswordHasher):
    """Hash raw passwords using bcrypt."""

    def __init__(self, rounds: int = 12) -> None:
        """Initialize hasher with work factor.

        Args:
            rounds: Bcrypt cost factor (recommended 10-14).
        """
        if rounds < 4:
            raise ValueError("Bcrypt rounds must be >= 4.")
        self._rounds = rounds

    @override
    def hash(self, raw_password: UserRawPassword) -> UserPasswordHash:
        """Return bcrypt hash for the given password.

        Args:
            raw_password: Raw password value object.

        Returns:
            UserPasswordHash: Encoded bcrypt hash bytes.
        """
        salt = bcrypt.gensalt(
            rounds=self._rounds
        )  # Generate salt with configured cost.
        return UserPasswordHash(bcrypt.hashpw(raw_password.value.encode(), salt))


class BcryptPasswordVerifier(PasswordVerifier):
    """Verify raw passwords against bcrypt hashes."""

    @override
    def verify(
        self, raw_password: UserRawPassword, hashed_password: UserPasswordHash
    ) -> bool:
        """Return True if raw_password matches the hashed_password.

        Args:
            raw_password: Raw password value object.
            hashed_password: Stored bcrypt hash value object.

        Returns:
            bool: True when password matches.
        """
        return bcrypt.checkpw(raw_password.value.encode(), hashed_password.value)
