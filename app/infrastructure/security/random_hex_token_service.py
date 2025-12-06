"""Service for generating and hashing refresh tokens."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Callable


class RandomHEXTokenService:
    """Generate and hash refresh tokens for secure storage."""

    def __init__(
        self,
        token_length: int = 32,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize service.

        Args:
            token_length: Length of token in bytes (default 32 = 256 bits).
            clock: Optional time source for tests.
        """
        if token_length < 16:
            raise ValueError("Token length must be >= 16 bytes")
        self._token_length = token_length
        self._clock = clock or self._utcnow

    def generate(self) -> str:
        """Generate a cryptographically secure random token.

        Returns:
            str: Hex-encoded token (length = token_length * 2 chars).
        """
        return secrets.token_hex(self._token_length)

    def hash(self, token: str) -> str:
        """Hash a refresh token for storage.

        Args:
            token: Plaintext refresh token.

        Returns:
            str: SHA-256 hash as hex string (64 chars).
        """
        return hashlib.sha256(token.encode()).hexdigest()

    def verify(self, token: str, token_hash: str) -> bool:
        """Verify a token matches its hash.

        Args:
            token: Plaintext token to verify.
            token_hash: Stored hash to compare against.

        Returns:
            bool: True if token matches hash.
        """
        return secrets.compare_digest(self.hash(token), token_hash)

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)
