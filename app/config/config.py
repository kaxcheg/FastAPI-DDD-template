from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal, ClassVar

from pydantic import PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_PREFIX = "FASTAPI_DDD_TEMPLATE_"

# All settings live here.
class BaseConfig(BaseSettings):
    """Common application settings."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_prefix=APP_PREFIX,
        extra="ignore",
    )

    ENV: Literal["dev", "test", "prod"]
    DEBUG: bool
    LOG_DIR: str

    JWT_ALGORITHM: str
    JWT_TOKEN_EXPIRY_TIME: int
    JWT_SECRET: SecretStr

    POSTGRES_DRIVER: Literal["postgresql+asyncpg", "postgresql+psycopg"] = (
        "postgresql+asyncpg"
    )
    POSTGRES_USER: str
    POSTGRES_USER_SECRET: SecretStr
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"

    UVICORN_HOST: str
    UVICORN_PORT: int

    APP_BOOTSTRAP_ADMIN: bool = False
    APP_ADMIN: str
    APP_ADMIN_PASSWORD_HASH: SecretStr

    @field_validator("JWT_TOKEN_EXPIRY_TIME")
    @classmethod
    def _positive(cls, v: int) -> int:
        """Ensure token expiry is positive."""
        if v <= 0:
            raise ValueError("JWT_TOKEN_EXPIRY_TIME must be positive")
        return v

    @property
    def POSTGRES_URL(self) -> PostgresDsn:
        """Return built DSN."""
        return PostgresDsn.build(
            scheme=self.POSTGRES_DRIVER,
            username=self.POSTGRES_USER,
            password=self.POSTGRES_USER_SECRET.get_secret_value(),
            host=self.POSTGRES_HOST,
            port=5432,
            path=f"{self.POSTGRES_DB}",
        )


class DevConfig(BaseConfig):
    """Development configuration."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env.dev",
        env_prefix=APP_PREFIX,
        secrets_dir="/run/secrets",
        extra="ignore",
    )

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
        env_prefix=APP_PREFIX,
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
        env_prefix=APP_PREFIX,
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

# Cache config instance to avoid recreating settings on every import.
@lru_cache
def get_settings() -> BaseConfig:
    """Return singleton config by ENV."""
    env = os.getenv(f"{APP_PREFIX}ENV")
    if not env:
        raise ValueError(f"{APP_PREFIX}ENV cannot be empty")

    match env.lower():
        case "dev":
            return DevConfig()  # pyright: ignore[reportCallIssue]
        case "test":
            return TestConfig() # pyright: ignore[reportCallIssue]
        case "prod":
            return ProdConfig() # pyright: ignore[reportCallIssue]
        case _:
            raise ValueError(f"Unknown ENV value: {env.lower()}")
