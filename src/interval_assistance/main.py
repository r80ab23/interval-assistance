"""Process entry point: `uvicorn interval_assistance.main:app_factory --factory`."""

from __future__ import annotations

from fastapi import FastAPI

from interval_assistance.api.app import create_app
from interval_assistance.core.config import get_settings
from interval_assistance.core.logging import configure_logging


def app_factory() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format.value)
    return create_app(settings)
