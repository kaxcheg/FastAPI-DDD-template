from __future__ import annotations

import os
from functools import lru_cache
from typing import ClassVar, Literal

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# All settings live here.
class BaseConfig(BaseSettings):
    """Common application settings."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        extra="ignore",
    )

    ENV: Literal["dev", "test", "prod"]
    DEBUG: bool

    JWT_ALGORITHM: str
    JWT_SECRET: SecretStr
    JWT_TOKEN_EXPIRY: int = 60  # in minutes (1 hour)
    REFRESH_TOKEN_EXPIRY: int = 43200  # in minutes (30 days)
    REFRESH_TOKEN_LENGTH: int = 32

    SESSION_EXPIRY_TIME: int = 43200  # in minutes (30 days, matches refresh token)
    MAX_CONCURRENT_SESSIONS: int = 5

    COOKIE_SECURE: bool = True  # HTTPS only in production
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "lax"
    COOKIE_DOMAIN: str | None = None  # None = current domain only
    COOKIE_PATH: str = "/"

    DB_PATH: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_DRIVER: str
    DB_USER: str
    DB_USER_SECRET: SecretStr
    DB_TABLE_SCHEMA: str

    BOOTSTRAP_FLAG: bool = True
    BOOTSTRAP_ADMIN: str
    BOOTSTRAP_ADMIN_PASSWORD_HASH: SecretStr

    @field_validator("JWT_TOKEN_EXPIRY", "REFRESH_TOKEN_EXPIRY")
    @classmethod
    def _positive_expiry(cls, v: int) -> int:
        """Ensure token expiry is positive."""
        if v <= 0:
            raise ValueError("Token expiry must be positive")
        return v

    @field_validator("REFRESH_TOKEN_EXPIRY")
    @classmethod
    def _refresh_longer_than_access(cls, v: int, info) -> int:
        """Ensure refresh token lives longer than access token."""
        access_expiry = info.data.get("JWT_TOKEN_EXPIRY", 60)
        if v <= access_expiry:
            raise ValueError("Refresh token expiry must be > access token expiry")
        return v

    @property
    def DB_URL(self) -> PostgresDsn:
        """Return built DSN."""
        return PostgresDsn.build(
            scheme=self.DB_DRIVER,
            username=self.DB_USER,
            password=self.DB_USER_SECRET.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT,
            path=f"{self.DB_PATH}",
        )


class DevConfig(BaseConfig):
    """Development configuration."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env.dev",
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    COOKIE_SECURE: bool = False  # Allow HTTP in development

    @field_validator("DEBUG")
    @classmethod
    def _enforce_debug_true(cls, v: bool) -> bool:
        """Ensure DEBUG is True in development."""
        if not v:
            raise ValueError("DEBUG must be True in development")
        return v


class TestConfig(BaseConfig):
    """Testing configuration."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=None,
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    @field_validator("DEBUG")
    @classmethod
    def _enforce_debug_false(cls, v: bool) -> bool:
        """Ensure DEBUG is False in testing."""
        if v:
            raise ValueError("DEBUG must be False in testing")
        return v


class ProdConfig(BaseConfig):
    """Production configuration."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=None,
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    @field_validator("DEBUG")
    @classmethod
    def _enforce_debug_false(cls, v: bool) -> bool:
        """Ensure DEBUG is False in production."""
        if v:
            raise ValueError("DEBUG must be False in production")
        return v

    @field_validator("JWT_SECRET")
    @classmethod
    def _check_secret(cls, v: SecretStr) -> SecretStr:
        """Deny weak secrets in production."""
        if "secret" in v.get_secret_value():
            raise ValueError("Invalid JWT_SECRET in production")
        return v

    @field_validator("COOKIE_SECURE")
    @classmethod
    def _enforce_secure_cookie(cls, v: bool) -> bool:
        """Ensure cookies are secure in production."""
        if not v:
            raise ValueError("COOKIE_SECURE must be True in production")
        return v


# Cache config instance to avoid recreating settings on every import.
@lru_cache
def get_settings() -> BaseConfig:
    """Return singleton config by ENV."""
    env = os.getenv("ENV")
    if not env:
        raise ValueError("ENV cannot be empty")

    match env.lower():
        case "dev":
            return DevConfig()  # type: ignore[call-arg]
        case "test":
            return TestConfig()  # type: ignore[call-arg]
        case "prod":
            return ProdConfig()  # type: ignore[call-arg]
        case _:
            raise ValueError(f"Unknown ENV value: {env.lower()}")
