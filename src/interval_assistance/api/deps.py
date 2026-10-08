"""Dependency accessors for app-scoped collaborators (clock, ids, settings, database)."""

from __future__ import annotations

import uuid
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from interval_assistance.core.clock import Clock
from interval_assistance.core.config import Settings
from interval_assistance.core.ids import IdGenerator
from interval_assistance.storage.engine import session_scope


def get_settings_dep(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_id_generator(request: Request) -> IdGenerator:
    ids: IdGenerator = request.app.state.id_generator
    return ids


def get_request_id(request: Request) -> uuid.UUID:
    request_id: uuid.UUID = request.state.request_id
    return request_id


def get_session(request: Request) -> Iterator[Session]:
    yield from session_scope(request.app.state.session_factory)
