from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

from interval_assistance.storage.alembic_helpers import make_alembic_config
from interval_assistance.storage.base import Base


def test_metadata_defines_no_tables() -> None:
    assert not Base.metadata.tables


def test_single_empty_baseline_revision() -> None:
    script = ScriptDirectory.from_config(make_alembic_config())
    revisions = list(script.walk_revisions())
    assert [r.revision for r in revisions] == ["0001"]
    assert script.get_current_head() == "0001"


def test_upgrade_and_downgrade_create_no_domain_tables(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'm.db'}"
    config = make_alembic_config(url)
    engine = create_engine(url)

    command.upgrade(config, "head")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    command.check(config)  # models and migrations agree (both empty)

    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()
