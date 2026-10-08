from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from interval_assistance.core.auth import Role
from interval_assistance.core.clock import ManualClock, SystemClock
from interval_assistance.core.config import Environment, Settings
from interval_assistance.core.ids import SequentialIdGenerator, UuidGenerator
from interval_assistance.core.logging import (
    REDACTED,
    JsonFormatter,
    SensitiveDataFilter,
)


def test_manual_clock_advances_deterministically() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    clock = ManualClock(start)
    clock.advance(2.5)
    assert clock.now_utc() == start + timedelta(seconds=2.5)
    assert clock.monotonic() == 2.5
    with pytest.raises(ValueError):
        clock.advance(-1)


def test_manual_clock_requires_utc() -> None:
    with pytest.raises(ValueError):
        ManualClock(datetime(2026, 1, 1))


def test_system_clock_is_timezone_aware() -> None:
    assert SystemClock().now_utc().tzinfo is not None


def test_sequential_ids_are_deterministic_and_unique() -> None:
    a, b = SequentialIdGenerator(), SequentialIdGenerator()
    first = [a.new_id() for _ in range(3)]
    assert first == [b.new_id() for _ in range(3)]
    assert len(set(first)) == 3


def test_uuid_generator_returns_uuid4() -> None:
    value = UuidGenerator().new_id()
    assert isinstance(value, uuid.UUID) and value.version == 4


def test_settings_reject_dev_identity_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            database_url="postgresql://u@h/db",
            dev_identity_enabled=True,
        )


def test_settings_production_requires_postgresql() -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            environment=Environment.PRODUCTION,
            database_url="sqlite:///x.db",
        )


def test_settings_reject_unsupported_backend() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="mysql://u@h/db")


def test_settings_default_has_no_dev_identity() -> None:
    settings = Settings(_env_file=None)
    assert settings.dev_identity_enabled is False
    assert settings.dev_identity_role is Role.COACH


def test_logging_redacts_sensitive_fields() -> None:
    record = logging.LogRecord("t", logging.INFO, __file__, 1, "msg", None, None)
    record.bpm = 150
    record.request_id = "abc"
    assert SensitiveDataFilter().filter(record)
    payload = json.loads(JsonFormatter().format(record))
    assert payload["bpm"] == REDACTED
    assert payload["request_id"] == "abc"
    assert "150" not in json.dumps(payload)
