"""Application settings (Pydantic Settings). No credentials in source; use environment or .env."""

from __future__ import annotations

import uuid
from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from interval_assistance.core.auth import Role

# Fixed so that the development identity is stable across runs.
DEV_IDENTITY_ID = uuid.UUID("00000000-0000-4000-8000-000000000001")

SUPPORTED_DB_BACKENDS = {"sqlite", "postgresql"}


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class LogFormat(StrEnum):
    JSON = "json"
    CONSOLE = "console"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="IA_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    environment: Environment = Environment.DEVELOPMENT
    database_url: str = "sqlite:///./interval_assistance.db"
    log_level: str = "INFO"
    log_format: LogFormat = LogFormat.JSON
    dev_identity_enabled: bool = False
    dev_identity_role: Role = Role.COACH

    @model_validator(mode="after")
    def _check(self) -> Self:
        backend = make_url(self.database_url).get_backend_name()
        if backend not in SUPPORTED_DB_BACKENDS:
            raise ValueError(f"unsupported database backend: {backend!r}")
        if self.environment is Environment.PRODUCTION:
            if self.dev_identity_enabled:
                raise ValueError("the development identity must not be enabled in production")
            if backend != "postgresql":
                raise ValueError("production requires a PostgreSQL database_url")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
