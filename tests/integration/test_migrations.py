from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from interval_assistance.storage.alembic_helpers import make_alembic_config
from interval_assistance.storage.base import Base

PART_2A_TABLES = {
    "sensor",
    "recording_session",
    "sensor_sample",
    "processing_run",
    "signal_assessment",
}


def test_metadata_defines_exactly_the_part_2a_tables() -> None:
    from interval_assistance.storage import models  # noqa: F401

    assert set(Base.metadata.tables) == PART_2A_TABLES


def test_revision_chain_is_baseline_then_part_2a() -> None:
    script = ScriptDirectory.from_config(make_alembic_config())
    revisions = {r.revision: r.down_revision for r in script.walk_revisions()}
    assert revisions == {"0002": "0001", "0001": None}
    assert script.get_current_head() == "0002"


def test_upgrade_creates_exactly_the_part_2a_tables_and_downgrade_removes_them(
    tmp_path: Path,
) -> None:
    url = f"sqlite:///{tmp_path / 'm.db'}"
    config = make_alembic_config(url)
    engine = create_engine(url)

    command.upgrade(config, "0001")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) == PART_2A_TABLES | {"alembic_version"}
    command.check(config)  # models and migrations agree

    command.downgrade(config, "0001")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}

    command.upgrade(config, "head")  # the cycle is repeatable
    assert set(inspect(engine).get_table_names()) == PART_2A_TABLES | {"alembic_version"}
    engine.dispose()


def test_alembic_check_detects_drift(tmp_path: Path) -> None:
    from alembic.util import CommandError

    url = f"sqlite:///{tmp_path / 'drift.db'}"
    config = make_alembic_config(url)
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql("CREATE TABLE unexpected (id INTEGER PRIMARY KEY)")
    engine.dispose()
    with pytest.raises(CommandError):
        command.check(config)
