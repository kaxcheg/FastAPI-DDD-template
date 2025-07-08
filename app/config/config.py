# -----------------------------------------------------------------------------
# Settings loading priority (Pydantic BaseSettings)
# Class attributes in BaseSettings are loaded in the following order:
#
# 1. Environment variables        → Highest priority
# 2. .env file (if specified)     → Loaded automatically via `env_file=".env"` in SettingsConfigDict
# 3. Default values in the model  → Used only if not set in env vars or .env
#
# .env or enviromental variables provide values for settings
# classes provide validation
# default values are not set explicitly
# -----------------------------------------------------------------------------
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import PostgresDsn, field_validator
import os

APP_PREFIX = "FAST_API_DDD_TEMPLATE_"

env = os.getenv(APP_PREFIX+"ENV")
if not env:
    raise ValueError(f"{APP_PREFIX}ENV cannot be empty")

# List all settings here
class BaseConfig(BaseSettings):
    """Common app settings with basic validation."""
    model_config = SettingsConfigDict(
        env_prefix=APP_PREFIX, extra="ignore"
    )

    # === Raw env vars ===
    DEBUG: bool
    LOG_DIR: str
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    JWT_TOKEN_EXPIRY_TIME: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "localhost"
    POSTGRES_DRIVER: Literal["asyncpg", "psycopg"] = "asyncpg"
    POSTGRES_PORT: int = 5432
    UVICORN_HOST: str
    UVICORN_PORT: int

    # === Validation ===
    @field_validator("JWT_TOKEN_EXPIRY_TIME")
    @classmethod
    def _positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("JWT_TOKEN_EXPIRY_TIME must be positive")
        return v

    # === Derived value ===
    @property
    def POSTGRES_URL(self) -> PostgresDsn:       
        """Build DSN from atomic parts."""
        return PostgresDsn.build(             
            scheme=f"postgresql+{self.POSTGRES_DRIVER}",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )    

# Development config
class DevConfig(BaseConfig):
    model_config = SettingsConfigDict(env_file=f".env.dev", env_prefix=APP_PREFIX, extra="ignore")
    
    @field_validator("DEBUG")
    @classmethod
    def enforce_debug_true(cls, v: bool) -> bool:
        if v is False:
            raise ValueError("DEBUG must be True in development")
        return v

# Testing config
class TestConfig(BaseConfig):
    model_config = SettingsConfigDict(env_file=None, env_prefix=APP_PREFIX, extra="ignore")
    
    @field_validator("DEBUG")
    @classmethod
    def enforce_debug_false(cls, v: bool) -> bool:
        if v is True:
            raise ValueError("DEBUG must be False in testing")
        return v

# Production config
class ProdConfig(BaseConfig):
    model_config = SettingsConfigDict(env_file=None, env_prefix=APP_PREFIX, extra="ignore")
    
    @field_validator("DEBUG")
    @classmethod
    def enforce_debug_false(cls, v: bool) -> bool:
        if v is True:
            raise ValueError("DEBUG must be False in production")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def check_dev_secret(cls, v: str) -> str:
        if "secret" in v:
            raise ValueError("Invalid JWT_SECRET_KEY in production")
        return v

def get_settings() -> BaseConfig:
    assert isinstance(env, str)
    match env.lower():
        case "dev":
            return_config = DevConfig() # pyright: ignore[reportCallIssue]
        case "test":
            return_config = TestConfig() # pyright: ignore[reportCallIssue]
        case "prod":
            return_config = ProdConfig() # pyright: ignore[reportCallIssue]
        case _:
            raise ValueError(f"Unknown ENV value: {env.lower()}")

    return return_config

settings = get_settings()
