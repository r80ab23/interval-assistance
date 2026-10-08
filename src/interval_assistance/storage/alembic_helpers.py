"""Programmatic Alembic helpers (also used by tests)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def make_alembic_config(database_url: str | None = None) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    if database_url is not None:
        config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config
