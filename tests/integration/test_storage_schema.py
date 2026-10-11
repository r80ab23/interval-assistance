"""Constraint, parity and dialect tests for the Phase 2a schema (migration `0002`).

The database under test is built by running the migration, not `create_all`, so these tests
exercise what actually ships. Engines come from `create_db_engine` so SQLite foreign keys are on.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from sqlalchemy import CheckConstraint, Engine, UniqueConstraint, insert, inspect
from sqlalchemy.dialects.postgresql.base import PGDialect
from sqlalchemy.engine import Dialect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.schema import CreateIndex, CreateTable

from interval_assistance.sensors.sample import SourceKind
from interval_assistance.signal import QualityState
from interval_assistance.storage import models
from interval_assistance.storage.alembic_helpers import make_alembic_config
from interval_assistance.storage.base import Base
from interval_assistance.storage.engine import create_db_engine

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
TABLES = Base.metadata.tables
POSTGRES_IDENTIFIER_LIMIT = 63
PART_2A = ["sensor", "recording_session", "processing_run", "sensor_sample", "signal_assessment"]


def new_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    url = f"sqlite:///{tmp_path / 'schema.db'}"
    command.upgrade(make_alembic_config(url), "head")
    created = create_db_engine(url)
    yield created
    created.dispose()


def sensor_row(**changes: Any) -> dict[str, Any]:
    return {
        "id": new_id(),
        "kind": "simulator",
        "external_identifier": None,
        "created_at": NOW,
    } | changes


def session_row(sensor_id: uuid.UUID, **changes: Any) -> dict[str, Any]:
    return {
        "id": new_id(),
        "sensor_id": sensor_id,
        "source_kind": "simulated",
        "is_synthetic": True,
        "started_at": NOW,
        "ended_at": None,
        "end_reason": None,
        "signal_quality_config_id": "cfg",
        "signal_quality_config_version": "1",
        "signal_quality_config_hash": "0" * 64,
        "origin_recording_session_id": None,
    } | changes


def run_row(session_id: uuid.UUID, **changes: Any) -> dict[str, Any]:
    return {
        "id": new_id(),
        "recording_session_id": session_id,
        "method_id": "signal_assessment",
        "method_version": "1",
        "software_version": "0",
        "parameters": {"k": 1},
        "created_at": NOW,
        "actor": "system",
        "is_synthetic": True,
    } | changes


def sample_row(session_id: uuid.UUID, sequence: int = 1, **changes: Any) -> dict[str, Any]:
    return {
        "id": new_id(),
        "recording_session_id": session_id,
        "sequence": sequence,
        "received_hr": 60.0,
        "received_hr_nonfinite": None,
        "raw_payload": None,
        "device_timestamp": None,
        "received_at": NOW,
        "ingestion_timestamp": NOW,
        "elapsed_seconds": 0.0,
        "source_kind": "simulated",
        "is_synthetic": True,
        "adapter_quality_hint": None,
        "origin_sample_id": None,
    } | changes


def assessment_row(session_id: uuid.UUID, run_id: uuid.UUID, **changes: Any) -> dict[str, Any]:
    return {
        "id": new_id(),
        "recording_session_id": session_id,
        "processing_run_id": run_id,
        "sample_id": None,
        "range_start_at": None,
        "range_end_at": None,
        "after_sample_id": None,
        "before_sample_id": None,
        "quality_state": "GOOD",
        "reasons": [],
        "created_at": NOW,
    } | changes


class Seed:
    """A sensor, a session, its run and one sample, inserted through Core."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.sensor = sensor_row()
        self.session = session_row(self.sensor["id"])
        self.run = run_row(self.session["id"])
        self.sample = sample_row(self.session["id"])
        with engine.begin() as connection:
            connection.execute(insert(TABLES["sensor"]), self.sensor)
            connection.execute(insert(TABLES["recording_session"]), self.session)
            connection.execute(insert(TABLES["processing_run"]), self.run)
            connection.execute(insert(TABLES["sensor_sample"]), self.sample)

    def add(self, table: str, row: dict[str, Any]) -> None:
        with self.engine.begin() as connection:
            connection.execute(insert(TABLES[table]), row)


@pytest.fixture
def seed(engine: Engine) -> Seed:
    return Seed(engine)


# --- valid rows are accepted -------------------------------------------------------------


def test_a_complete_valid_graph_is_accepted(seed: Seed) -> None:
    sid, rid = seed.session["id"], seed.run["id"]
    seed.add("sensor_sample", sample_row(sid, 2, received_hr=None, received_hr_nonfinite="nan"))
    seed.add("signal_assessment", assessment_row(sid, rid, sample_id=seed.sample["id"]))
    seed.add(
        "signal_assessment",
        assessment_row(
            sid,
            rid,
            quality_state="MISSING",
            reasons=["gap"],
            range_start_at=NOW,
            range_end_at=NOW + timedelta(seconds=9),
            after_sample_id=seed.sample["id"],
            before_sample_id=seed.sample["id"],
        ),
    )


def test_replay_session_and_sample_link_back_to_their_origins(seed: Seed) -> None:
    replay_sensor = sensor_row(kind="replay")
    seed.add("sensor", replay_sensor)
    replay = session_row(
        replay_sensor["id"],
        source_kind="replay",
        origin_recording_session_id=seed.session["id"],
    )
    seed.add("recording_session", replay)
    seed.add(
        "sensor_sample",
        sample_row(replay["id"], source_kind="replay", origin_sample_id=seed.sample["id"]),
    )


# --- foreign keys ------------------------------------------------------------------------


def test_sqlite_foreign_keys_are_enforced(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
    with pytest.raises(IntegrityError), engine.begin() as connection:
        connection.execute(insert(TABLES["recording_session"]), session_row(new_id()))


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("recording_session", "origin_recording_session_id"),
        ("processing_run", "recording_session_id"),
        ("sensor_sample", "recording_session_id"),
        ("sensor_sample", "origin_sample_id"),
        ("signal_assessment", "recording_session_id"),
        ("signal_assessment", "processing_run_id"),
        ("signal_assessment", "sample_id"),
        ("signal_assessment", "after_sample_id"),
        ("signal_assessment", "before_sample_id"),
    ],
)
def test_every_foreign_key_rejects_a_dangling_reference(
    seed: Seed, table: str, column: str
) -> None:
    sid, rid = seed.session["id"], seed.run["id"]
    rows: dict[str, dict[str, Any]] = {
        "recording_session": session_row(seed.sensor["id"]),
        "processing_run": run_row(sid),
        "sensor_sample": sample_row(sid, 2),
        "signal_assessment": assessment_row(
            sid,
            rid,
            range_start_at=NOW,
            range_end_at=NOW,
            after_sample_id=seed.sample["id"],
        ),
    }
    row = rows[table] | {column: new_id()}
    with pytest.raises(IntegrityError):
        seed.add(table, row)


def test_referenced_rows_cannot_be_deleted(seed: Seed) -> None:
    with pytest.raises(IntegrityError), seed.engine.begin() as connection:
        connection.execute(TABLES["sensor"].delete())


# --- check constraints -------------------------------------------------------------------


def test_sensor_kind_is_limited_to_part_2a_kinds(engine: Engine) -> None:
    for kind in ("simulator", "manual", "replay"):
        with engine.begin() as connection:
            connection.execute(insert(TABLES["sensor"]), sensor_row(kind=kind))
    for kind in ("polar_h10", "generic_ble_hr", ""):
        with pytest.raises(IntegrityError), engine.begin() as connection:
            connection.execute(insert(TABLES["sensor"]), sensor_row(kind=kind))


def test_session_source_kind_values(seed: Seed) -> None:
    for value in ("real", "simulated", "replay", "manual"):
        seed.add("recording_session", session_row(seed.sensor["id"], source_kind=value))
    with pytest.raises(IntegrityError):
        seed.add("recording_session", session_row(seed.sensor["id"], source_kind="virtual"))


def test_sample_source_kind_values(seed: Seed) -> None:
    sid = seed.session["id"]
    for sequence, value in enumerate(("real", "simulated", "replay", "manual"), start=2):
        seed.add("sensor_sample", sample_row(sid, sequence, source_kind=value))
    with pytest.raises(IntegrityError):
        seed.add("sensor_sample", sample_row(sid, 9, source_kind="virtual"))


def test_end_reason_values(seed: Seed) -> None:
    for reason in (None, "completed", "interrupted"):
        seed.add("recording_session", session_row(seed.sensor["id"], end_reason=reason))
    with pytest.raises(IntegrityError):
        seed.add("recording_session", session_row(seed.sensor["id"], end_reason="crashed"))


@pytest.mark.parametrize("sequence", [0, -1])
def test_sequence_must_be_positive(seed: Seed, sequence: int) -> None:
    with pytest.raises(IntegrityError):
        seed.add("sensor_sample", sample_row(seed.session["id"], sequence))


def test_elapsed_seconds_cannot_be_negative(seed: Seed) -> None:
    seed.add("sensor_sample", sample_row(seed.session["id"], 2, elapsed_seconds=0))
    with pytest.raises(IntegrityError):
        seed.add("sensor_sample", sample_row(seed.session["id"], 3, elapsed_seconds=-0.001))


@pytest.mark.parametrize("marker", ["nan", "+inf", "-inf"])
def test_nonfinite_marker_requires_a_null_value(seed: Seed, marker: str) -> None:
    sid = seed.session["id"]
    seed.add("sensor_sample", sample_row(sid, 2, received_hr=None, received_hr_nonfinite=marker))
    with pytest.raises(IntegrityError):  # marker with a finite value
        seed.add(
            "sensor_sample", sample_row(sid, 3, received_hr=60.0, received_hr_nonfinite=marker)
        )


@pytest.mark.parametrize("marker", ["inf", "NaN", "Infinity", "", "+Inf"])
def test_nonfinite_marker_is_one_of_the_three_classes(seed: Seed, marker: str) -> None:
    with pytest.raises(IntegrityError):
        seed.add(
            "sensor_sample",
            sample_row(seed.session["id"], 2, received_hr=None, received_hr_nonfinite=marker),
        )


def test_null_value_without_marker_is_a_valid_malformed_sample(seed: Seed) -> None:
    seed.add(
        "sensor_sample",
        sample_row(seed.session["id"], 2, received_hr=None, raw_payload=b"\x00\x7f"),
    )


def test_quality_state_values(seed: Seed) -> None:
    sid, rid, after = seed.session["id"], seed.run["id"], seed.sample["id"]
    range_form = {"range_start_at": NOW, "range_end_at": NOW, "after_sample_id": after}
    for state in QualityState:
        seed.add(
            "signal_assessment",
            assessment_row(sid, rid, quality_state=state.value, **range_form),
        )
    with pytest.raises(IntegrityError):
        seed.add("signal_assessment", assessment_row(sid, rid, quality_state="good", **range_form))


@pytest.mark.parametrize(
    "changes",
    [
        {},  # neither form
        {"sample_id": "S", "range_start_at": NOW},  # per-sample with a range field
        {"sample_id": "S", "range_end_at": NOW},
        {"sample_id": "S", "after_sample_id": "S"},
        {"sample_id": "S", "before_sample_id": "S"},
        {"range_end_at": NOW, "after_sample_id": "S"},  # range missing its start
        {"range_start_at": NOW, "after_sample_id": "S"},  # range missing its end
        {"range_start_at": NOW, "range_end_at": NOW},  # range missing after_sample_id
        {"before_sample_id": "S"},  # only before
    ],
)
def test_single_form_rejects_mixed_or_incomplete_rows(seed: Seed, changes: dict[str, Any]) -> None:
    resolved = {k: (seed.sample["id"] if v == "S" else v) for k, v in changes.items()}
    with pytest.raises(IntegrityError):
        seed.add(
            "signal_assessment", assessment_row(seed.session["id"], seed.run["id"], **resolved)
        )


def test_open_ended_range_has_no_before_sample(seed: Seed) -> None:
    seed.add(
        "signal_assessment",
        assessment_row(
            seed.session["id"],
            seed.run["id"],
            quality_state="STALE",
            reasons=["stale"],
            range_start_at=NOW,
            range_end_at=NOW + timedelta(seconds=10),
            after_sample_id=seed.sample["id"],
            before_sample_id=None,
        ),
    )


# --- uniqueness --------------------------------------------------------------------------


def test_sequence_is_unique_per_session_only(seed: Seed) -> None:
    with pytest.raises(IntegrityError):
        seed.add("sensor_sample", sample_row(seed.session["id"], 1))
    other = session_row(seed.sensor["id"])
    seed.add("recording_session", other)
    seed.add("sensor_sample", sample_row(other["id"], 1))  # same sequence, another session


def test_duplicate_per_sample_assessment_in_a_run_is_rejected(seed: Seed) -> None:
    sid, rid, sample_id = seed.session["id"], seed.run["id"], seed.sample["id"]
    seed.add("signal_assessment", assessment_row(sid, rid, sample_id=sample_id))
    with pytest.raises(IntegrityError):
        seed.add("signal_assessment", assessment_row(sid, rid, sample_id=sample_id))
    other_run = run_row(sid)
    seed.add("processing_run", other_run)  # another run may assess the same sample
    seed.add("signal_assessment", assessment_row(sid, other_run["id"], sample_id=sample_id))


def test_repeated_run_null_pairs_are_accepted_for_range_rows(seed: Seed) -> None:
    sid, rid = seed.session["id"], seed.run["id"]
    for offset in range(3):  # NULL sample_id values are distinct: no uniqueness for ranges
        seed.add(
            "signal_assessment",
            assessment_row(
                sid,
                rid,
                quality_state="MISSING",
                reasons=["gap"],
                range_start_at=NOW + timedelta(seconds=offset),
                range_end_at=NOW + timedelta(seconds=offset + 9),
                after_sample_id=seed.sample["id"],
            ),
        )
    identical = assessment_row(
        sid, rid, range_start_at=NOW, range_end_at=NOW, after_sample_id=seed.sample["id"]
    )
    seed.add("signal_assessment", identical)
    seed.add("signal_assessment", identical | {"id": new_id()})


def test_several_runs_may_share_a_recording_session(seed: Seed) -> None:
    """`processing_run.recording_session_id` is deliberately not unique (owner decision)."""
    seed.add("processing_run", run_row(seed.session["id"]))
    seed.add("processing_run", run_row(seed.session["id"]))


# --- nothing beyond the documented constraints -------------------------------------------


def test_only_the_two_documented_unique_constraints_exist(engine: Engine) -> None:
    inspector = inspect(engine)
    uniques = {
        table: [tuple(u["column_names"]) for u in inspector.get_unique_constraints(table)]
        for table in PART_2A
    }
    assert uniques == {
        "sensor": [],
        "recording_session": [],
        "processing_run": [],
        "sensor_sample": [("recording_session_id", "sequence")],
        "signal_assessment": [("processing_run_id", "sample_id")],
    }


def test_no_secondary_indexes_exist(engine: Engine) -> None:
    inspector = inspect(engine)
    assert {table: inspector.get_indexes(table) for table in PART_2A} == {t: [] for t in PART_2A}
    assert all(not table.indexes for table in TABLES.values())


def test_no_server_defaults_or_triggers(engine: Engine) -> None:
    with engine.connect() as connection:
        triggers = connection.exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        ).all()
    assert triggers == []
    assert all(
        column.server_default is None and column.default is None
        for table in TABLES.values()
        for column in table.columns
    )


# --- parity between the migration and the models -----------------------------------------


def test_migration_and_models_agree_on_constraint_names(engine: Engine) -> None:
    inspector = inspect(engine)
    for name in PART_2A:
        table = TABLES[name]
        assert inspector.get_pk_constraint(name)["name"] == table.primary_key.name
        assert {fk["name"] for fk in inspector.get_foreign_keys(name)} == {
            c.name for c in table.foreign_key_constraints
        }
        assert {u["name"] for u in inspector.get_unique_constraints(name)} == {
            c.name for c in table.constraints if isinstance(c, UniqueConstraint)
        }
        assert {c["name"] for c in inspector.get_check_constraints(name)} == {
            c.name for c in table.constraints if isinstance(c, CheckConstraint)
        }


def test_migration_and_models_agree_on_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    for name in PART_2A:
        migrated = {c["name"]: c["nullable"] for c in inspector.get_columns(name)}
        declared = {c.name: c.nullable for c in TABLES[name].columns}
        assert migrated == declared


def test_check_constraint_text_agrees_between_migration_and_models(engine: Engine) -> None:
    """Models and the handwritten migration repeat the same literals; compare their SQL."""

    def normal(text: str) -> str:
        return " ".join(text.replace("(", " ( ").replace(")", " ) ").split())

    inspector = inspect(engine)
    for name in PART_2A:
        migrated = {c["name"]: normal(c["sqltext"]) for c in inspector.get_check_constraints(name)}
        declared = {
            c.name: normal(str(c.sqltext))
            for c in TABLES[name].constraints
            if isinstance(c, CheckConstraint)
        }
        assert migrated == declared


# --- enum-list consistency with the domain (checked from outside the storage package) ----


def test_literal_lists_match_the_domain_enums() -> None:
    assert set(models.SOURCE_KINDS) == {kind.value for kind in SourceKind}
    assert set(models.QUALITY_STATES) == {state.value for state in QualityState}
    assert len(models.SOURCE_KINDS) == len(set(models.SOURCE_KINDS))
    assert len(models.QUALITY_STATES) == len(set(models.QUALITY_STATES))
    assert models.END_REASONS == ("completed", "interrupted")
    assert models.NONFINITE_CLASSES == ("nan", "+inf", "-inf")
    assert models.SENSOR_KINDS == ("simulator", "manual", "replay")


# --- PostgreSQL dialect compilation (no server or driver involved) ------------------------


def _postgres() -> Dialect:
    return PGDialect()  # type: ignore[no-untyped-call]  # SQLAlchemy ships it untyped


def _postgres_ddl() -> dict[str, str]:
    dialect = _postgres()
    return {
        name: str(CreateTable(table).compile(dialect=dialect)) for name, table in TABLES.items()
    }


def test_schema_compiles_for_postgresql() -> None:
    ddl = _postgres_ddl()
    assert set(ddl) == set(PART_2A)
    joined = "\n".join(ddl.values())
    assert "UUID" in joined and "TIMESTAMP WITH TIME ZONE" in joined and "JSON" in joined
    assert "BYTEA" in joined and "BOOLEAN" in joined and "FLOAT" in joined
    assert "NULLS NOT DISTINCT" not in joined.upper()
    assert "sqlite" not in joined.lower()
    for statement in ddl.values():
        assert statement.strip().startswith("CREATE TABLE")


def test_no_index_ddl_is_generated() -> None:
    dialect = _postgres()
    for table in TABLES.values():
        assert [str(CreateIndex(index).compile(dialect=dialect)) for index in table.indexes] == []


def test_all_identifiers_fit_the_postgresql_limit() -> None:
    names: list[str] = []
    for table in TABLES.values():
        names.append(table.name)
        names.extend(column.name for column in table.columns)
        names.extend(c.name for c in table.constraints if isinstance(c.name, str))
    assert all(len(name) <= POSTGRES_IDENTIFIER_LIMIT for name in names), [
        name for name in names if len(name) > POSTGRES_IDENTIFIER_LIMIT
    ]
    ddl = "\n".join(_postgres_ddl().values())
    assert "recording_session_origin_recording_session_id" not in ddl  # the 66-character name


def test_every_constraint_has_an_explicit_name() -> None:
    for table in TABLES.values():
        for constraint in table.constraints:
            assert constraint.name, (table.name, constraint)


def test_migration_constraint_names_fit_the_postgresql_limit(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'names.db'}"
    command.upgrade(make_alembic_config(url), "head")
    engine = create_db_engine(url)
    inspector = inspect(engine)
    names: list[str] = []
    for table in PART_2A:
        names.append(inspector.get_pk_constraint(table)["name"] or "")
        names.extend(fk["name"] or "" for fk in inspector.get_foreign_keys(table))
        names.extend(u["name"] or "" for u in inspector.get_unique_constraints(table))
        names.extend(c["name"] or "" for c in inspector.get_check_constraints(table))
    engine.dispose()
    assert all(names) and all(len(name) <= POSTGRES_IDENTIFIER_LIMIT for name in names)
