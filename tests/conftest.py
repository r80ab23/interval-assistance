from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from interval_assistance.api.app import create_app
from interval_assistance.core.auth import Role
from interval_assistance.core.clock import ManualClock
from interval_assistance.core.config import Environment, Settings
from interval_assistance.core.ids import SequentialIdGenerator

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(T0)


def make_settings(
    tmp_path: Path, *, dev_identity: bool = True, role: Role = Role.COACH
) -> Settings:
    return Settings(
        _env_file=None,
        environment=Environment.TEST,
        database_url=f"sqlite:///{tmp_path / 'test.db'}",
        dev_identity_enabled=dev_identity,
        dev_identity_role=role,
    )


@pytest.fixture
def client(tmp_path: Path, clock: ManualClock) -> Iterator[TestClient]:
    app = create_app(make_settings(tmp_path), clock=clock, id_generator=SequentialIdGenerator())
    with TestClient(app) as test_client:
        yield test_client
