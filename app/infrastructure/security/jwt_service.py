from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

from jwt import ExpiredSignatureError, InvalidTokenError, decode, encode
from pydantic import SecretStr


class JwtTokenError(Exception):
    """Base JWT service error."""


class JwtTokenInvalid(JwtTokenError):
    """Token failed validation or signature check."""


class JwtTokenExpired(JwtTokenError):
    """Token is expired."""


class JwtTokenService:
    """Issue and validate JWT tokens with configurable lifetime."""

    def __init__(
        self,
        secret: SecretStr,
        algorithm: str = "HS256",
        default_expires: timedelta | int | None = None,
        required_claims: Sequence[str] = ("sub", "exp"),
        leeway: int | float = 0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        """Initialize service configuration.

        Args:
            secret: HMAC key or private key depending on algorithm.
            algorithm: JWT algorithm (e.g., HS256, RS256).
            default_expires: Default lifetime as timedelta or seconds (None disables auto-exp).
            required_claims: Claims that must be present on decode().
            leeway: Allowed clock skew in seconds for exp verification.
            clock: Optional time source for tests.
        """
        self._secret = secret
        self._algorithm = algorithm
        if isinstance(default_expires, int):
            default_expires = timedelta(seconds=default_expires)
        self._default_expires = default_expires
        self._required_claims = tuple(required_claims)
        self._leeway = leeway
        self._clock = clock or self._utcnow

    def issue(
        self,
        claims: Mapping[str, Any],
        *,
        expires_in: timedelta | int | None = None,
        additional_headers: Mapping[str, Any] | None = None,
    ) -> str:
        """Return a signed JWT string.

        Args:
            claims: Base claims to encode.
            expires_in: Lifetime override as timedelta or seconds (defaults to service setting).
            additional_headers: Extra header fields (e.g., {"kid": "..."}).

        Returns:
            str: Encoded JWT.
        """
        to_encode = dict(claims)

        exp = self._compute_exp(expires_in)
        if exp is not None:
            # 'exp' should be an integer timestamp for compatibility.
            to_encode["exp"] = int(exp.timestamp())

        token = encode(
            payload=to_encode,
            key=self._secret.get_secret_value(),
            algorithm=self._algorithm,
            headers=dict(additional_headers) if additional_headers else None,
        )
        return token

    def decode(self, token: str, *, verify_exp: bool = True) -> dict[str, Any]:
        """Return decoded claims or raise on validation failure.

        Args:
            token: Encoded JWT.
            verify_exp: Whether to enforce expiration check.

        Raises:
            JwtTokenExpired: When the token is expired and expiration is verified.
            JwtTokenInvalid: When signature, structure, or required claims fail.

        Returns:
            dict[str, Any]: Decoded claims.
        """
        options = {
            "verify_signature": True,
            "verify_exp": verify_exp,
            "require": list(self._required_claims),
        }
        try:
            payload = decode(
                token,
                key=self._secret.get_secret_value(),
                algorithms=[self._algorithm],
                options=options,
                leeway=self._leeway,
            )
        except ExpiredSignatureError as e:
            raise JwtTokenExpired(str(e)) from None
        except InvalidTokenError as e:
            raise JwtTokenInvalid(str(e)) from None

        # Defensive check in case library options change.
        missing = [c for c in self._required_claims if c not in payload]
        if missing:
            raise JwtTokenInvalid(f"Missing required claims: {missing}")
        return payload

    def _compute_exp(self, override: timedelta | int | None) -> datetime | None:
        # Compute absolute expiration timestamp or None.
        if override is None:
            base = self._default_expires
        else:
            base = (
                timedelta(seconds=override) if isinstance(override, int) else override
            )
        if base is None:
            return None
        return self._clock() + base

    @staticmethod
    def _utcnow() -> datetime:
        # Always return timezone-aware UTC.
        return datetime.now(timezone.utc)
