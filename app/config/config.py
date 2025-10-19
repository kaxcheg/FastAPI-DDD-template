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

    FASTAPI_DDD_TEMPLATE_ENV: Literal["dev", "test", "prod"]
    FASTAPI_DDD_TEMPLATE_DEBUG: bool

    FASTAPI_DDD_TEMPLATE_JWT_ALGORITHM: str
    FASTAPI_DDD_TEMPLATE_JWT_TOKEN_EXPIRY_TIME: int
    FASTAPI_DDD_TEMPLATE_JWT_SECRET: SecretStr

    DB_PATH: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_DRIVER: str
    DB_USER: str
    DB_USER_SECRET: SecretStr
    DB_TABLE_SCHEMA: str

    FASTAPI_DDD_TEMPLATE_BOOTSTRAP_FLAG: bool
    FASTAPI_DDD_TEMPLATE_BOOTSTRAP_ADMIN: str
    FASTAPI_DDD_TEMPLATE_BOOTSTRAP_ADMIN_PASSWORD_HASH: SecretStr

    @field_validator("FASTAPI_DDD_TEMPLATE_JWT_TOKEN_EXPIRY_TIME")
    @classmethod
    def _positive(cls, v: int) -> int:
        """Ensure token expiry is positive."""
        if v <= 0:
            raise ValueError(
                "FASTAPI_DDD_TEMPLATE_JWT_TOKEN_EXPIRY_TIME must be positive"
            )
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

    @field_validator("FASTAPI_DDD_TEMPLATE_DEBUG")
    @classmethod
    def _enforce_debug_true(cls, v: bool) -> bool:
        """Ensure FASTAPI_DDD_TEMPLATE_DEBUG is True in development."""
        if not v:
            raise ValueError("FASTAPI_DDD_TEMPLATE_DEBUG must be True in development")
        return v


class TestConfig(BaseConfig):
    """Testing configuration."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=None,
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    @field_validator("FASTAPI_DDD_TEMPLATE_DEBUG")
    @classmethod
    def _enforce_debug_false(cls, v: bool) -> bool:
        """Ensure FASTAPI_DDD_TEMPLATE_DEBUG is False in testing."""
        if v:
            raise ValueError("FASTAPI_DDD_TEMPLATE_DEBUG must be False in testing")
        return v


class ProdConfig(BaseConfig):
    """Production configuration."""

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=None,
        secrets_dir="/run/secrets",
        extra="ignore",
    )

    @field_validator("FASTAPI_DDD_TEMPLATE_DEBUG")
    @classmethod
    def _enforce_debug_false(cls, v: bool) -> bool:
        """Ensure DEBUG is False in production."""
        if v:
            raise ValueError("FASTAPI_DDD_TEMPLATE_DEBUG must be False in production")
        return v

    @field_validator("FASTAPI_DDD_TEMPLATE_JWT_SECRET")
    @classmethod
    def _check_secret(cls, v: SecretStr) -> SecretStr:
        """Deny weak secrets in production."""
        if "secret" in v.get_secret_value():
            raise ValueError("Invalid FASTAPI_DDD_TEMPLATE_JWT_SECRET in production")
        return v


# Cache config instance to avoid recreating settings on every import.
@lru_cache
def get_settings() -> BaseConfig:
    """Return singleton config by FASTAPI_DDD_TEMPLATE_ENV."""
    env = os.getenv("FASTAPI_DDD_TEMPLATE_ENV")
    if not env:
        raise ValueError("FASTAPI_DDD_TEMPLATE_ENV cannot be empty")

    match env.lower():
        case "dev":
            return DevConfig()  # type: ignore[call-arg]
        case "test":
            return TestConfig()  # type: ignore[call-arg]
        case "prod":
            return ProdConfig()  # type: ignore[call-arg]
        case _:
            raise ValueError(f"Unknown FASTAPI_DDD_TEMPLATE_ENV value: {env.lower()}")
