"""Ingestion service against a migrated temporary SQLite database.

Clocks and ids are deterministic. Numeric values come from the documented test configuration
(`tests.unit.signal.helpers`), not from any physiological claim.
"""

from __future__ import annotations

import math
import uuid
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from interval_assistance import __version__
from interval_assistance.core.clock import Clock, ManualClock
from interval_assistance.core.errors import ConfigurationError, InvalidSensorSample
from interval_assistance.core.ids import SequentialIdGenerator
from interval_assistance.ingestion import (
    CLOSE_END_REASON,
    METHOD_ID,
    METHOD_VERSION,
    PROCESSING_ACTOR,
    IngestionService,
)
from interval_assistance.ingestion.mapping import sample_from_row
from interval_assistance.sensors.sample import HeartRateSample, SourceKind
from interval_assistance.signal import QualityState, StreamState, assess_sample
from interval_assistance.storage import repositories
from interval_assistance.storage.alembic_helpers import make_alembic_config
from interval_assistance.storage.engine import create_db_engine, create_session_factory
from interval_assistance.storage.models import (
    ProcessingRun,
    RecordingSession,
    Sensor,
    SensorSample,
    SignalAssessment,
)
from tests.unit.signal.helpers import SENSOR_ID, T0, make_config, sample

OTHER_SENSOR_ID = uuid.UUID(int=2)
FIRST_ID = 100  # generated ids start here, clear of the sensor ids


class Env:
    def __init__(self, engine: Engine, clock: Clock) -> None:
        self.engine = engine
        self.clock = clock
        self.factory: sessionmaker[Session] = create_session_factory(engine)
        self.ids = SequentialIdGenerator(FIRST_ID)
        self.service = IngestionService(self.factory, clock, self.ids)
        with self.factory() as db, db.begin():
            for sensor_id in (SENSOR_ID, OTHER_SENSOR_ID):
                db.add(Sensor(id=sensor_id, kind="simulator", created_at=T0))

    def open(self, **changes: Any) -> uuid.UUID:
        arguments: dict[str, Any] = {
            "sensor_id": SENSOR_ID,
            "source_kind": SourceKind.SIMULATED,
            "is_synthetic": True,
            "config": make_config(),
        } | changes
        return self.service.open_session(**arguments).session_id

    def count(self, model: type) -> int:
        with self.factory() as db:
            return db.execute(select(func.count()).select_from(model)).scalar_one()

    def samples(self, session_id: uuid.UUID) -> list[SensorSample]:
        with self.factory() as db:
            return repositories.list_raw_samples(db, session_id)

    def run_id(self, session_id: uuid.UUID) -> uuid.UUID:
        with self.factory() as db:
            return repositories.list_processing_runs(db, session_id)[0].id

    def assessments(self, session_id: uuid.UUID) -> list[SignalAssessment]:
        with self.factory() as db:
            return repositories.list_signal_assessments(db, self.run_id(session_id))

    def per_sample(self, session_id: uuid.UUID) -> list[SignalAssessment]:
        return [a for a in self.assessments(session_id) if a.sample_id is not None]

    def ranges(self, session_id: uuid.UUID) -> list[SignalAssessment]:
        return [a for a in self.assessments(session_id) if a.sample_id is None]

    def session_row(self, session_id: uuid.UUID) -> RecordingSession:
        with self.factory() as db:
            row = repositories.get_recording_session(db, session_id)
            assert row is not None
            return row


@pytest.fixture
def engine(tmp_path: Path) -> Iterator[Engine]:
    url = f"sqlite:///{tmp_path / 'ingest.db'}"
    command.upgrade(make_alembic_config(url), "head")
    created = create_db_engine(url)
    yield created
    created.dispose()


@pytest.fixture
def clock() -> ManualClock:
    return ManualClock(T0)


@pytest.fixture
def env(engine: Engine, clock: ManualClock) -> Env:
    return Env(engine, clock)


def boom(*_args: object, **_kwargs: object) -> None:
    raise RuntimeError("injected failure")


# --- open ----------------------------------------------------------------------------------


def test_open_creates_one_session_and_one_run_together(env: Env, clock: ManualClock) -> None:
    config = make_config()
    session_id = env.open(config=config)
    row = env.session_row(session_id)
    assert row.sensor_id == SENSOR_ID and row.source_kind == "simulated" and row.is_synthetic
    assert row.ended_at is None and row.end_reason is None
    assert row.origin_recording_session_id is None
    assert row.signal_quality_config_id == config.config_id
    assert row.signal_quality_config_version == config.config_version
    assert row.signal_quality_config_hash == config.config_hash()
    assert env.count(RecordingSession) == 1 and env.count(ProcessingRun) == 1
    with env.factory() as db:
        (run,) = repositories.list_processing_runs(db, session_id)
    assert run.method_id == METHOD_ID == "signal_assessment"
    assert run.method_version == METHOD_VERSION and run.software_version == __version__
    assert run.actor == PROCESSING_ACTOR == "system" and run.is_synthetic is True
    assert run.parameters == config.hashed_document()
    assert row.started_at == run.created_at


def test_open_with_an_unknown_sensor_fails_and_creates_nothing(env: Env) -> None:
    sensors_before = env.count(Sensor)
    with pytest.raises(InvalidSensorSample):
        env.open(sensor_id=uuid.UUID(int=999))
    assert env.count(Sensor) == sensors_before
    assert env.count(RecordingSession) == 0 and env.count(ProcessingRun) == 0


def test_open_failure_rolls_back_both_records_and_registers_nothing(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(repositories, "insert_processing_run", boom)
    with pytest.raises(RuntimeError, match="injected"):
        env.open()
    assert env.count(RecordingSession) == 0 and env.count(ProcessingRun) == 0
    with pytest.raises(InvalidSensorSample):  # the would-be session id is not active
        env.service.ingest(uuid.UUID(int=FIRST_ID), sample(15))
    monkeypatch.undo()
    assert env.service.ingest(env.open(), sample(15)).sequence == 1  # still usable afterwards


def test_open_rejects_a_changed_configuration_under_the_same_identity(env: Env) -> None:
    env.open()
    with pytest.raises(ConfigurationError):
        env.open(config=make_config(max_jump_bpm=6))
    assert env.count(RecordingSession) == 1 and env.count(ProcessingRun) == 1
    env.open(config=make_config(config_version="2", max_jump_bpm=6))  # a new version is fine
    env.open()  # same content again is fine
    assert env.count(RecordingSession) == 3


def test_open_validates_session_level_inputs(env: Env) -> None:
    with pytest.raises(ValueError, match="replay"):
        env.open(source_kind=SourceKind.REPLAY, is_synthetic=False)
    with pytest.raises(ValueError, match="synthetic"):
        env.open(source_kind=SourceKind.MANUAL, is_synthetic=False)
    assert env.count(RecordingSession) == 0
    env.open(source_kind=SourceKind.REAL, is_synthetic=False)  # a real session is not synthetic


# --- ingest ---------------------------------------------------------------------------------


def test_samples_get_consecutive_sequences_and_clock_derived_times(
    env: Env, clock: ManualClock
) -> None:
    session_id = env.open()
    for index in range(3):
        clock.advance(2.5)
        result = env.service.ingest(session_id, sample(15, seconds=index))
        assert result.sequence == index + 1
    rows = env.samples(session_id)
    assert [r.sequence for r in rows] == [1, 2, 3]
    assert [r.elapsed_seconds for r in rows] == [2.5, 5.0, 7.5]
    assert [r.ingestion_timestamp.replace(tzinfo=UTC) for r in rows] == [
        T0 + timedelta(seconds=s) for s in (2.5, 5.0, 7.5)
    ]
    assert all(r.recording_session_id == session_id for r in rows)
    assert len({r.id for r in rows}) == 3


def test_elapsed_seconds_come_only_from_the_monotonic_clock() -> None:
    class SplitClock(Clock):
        def __init__(self) -> None:
            self.wall = T0
            self.mono = 50.0

        def now_utc(self) -> datetime:
            return self.wall

        def monotonic(self) -> float:
            return self.mono

    split = SplitClock()
    # Not using the shared fixtures: this clock needs wall time and monotonic time to disagree.
    import tempfile

    with tempfile.TemporaryDirectory() as directory:
        url = f"sqlite:///{Path(directory) / 'split.db'}"
        command.upgrade(make_alembic_config(url), "head")
        engine = create_db_engine(url)
        try:
            env = Env(engine, split)
            session_id = env.open()
            split.wall = T0 + timedelta(days=1)  # the wall clock jumps; monotonic moves 2.25
            split.mono = 52.25
            env.service.ingest(session_id, sample(15))
            assert env.samples(session_id)[0].elapsed_seconds == 2.25
        finally:
            engine.dispose()


def test_raw_values_are_stored_exactly_as_received(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(None, raw_payload=b"\x00\x01"))
    env.service.ingest(session_id, sample(math.nan, seconds=1))
    env.service.ingest(session_id, sample(math.inf, seconds=2))
    env.service.ingest(session_id, sample(-math.inf, seconds=3))
    env.service.ingest(session_id, sample(15.25, seconds=4))
    rows = env.samples(session_id)
    assert [(r.received_hr, r.received_hr_nonfinite) for r in rows] == [
        (None, None),
        (None, "nan"),
        (None, "+inf"),
        (None, "-inf"),
        (15.25, None),
    ]
    assert rows[0].raw_payload == b"\x00\x01" and rows[1].raw_payload is None


def test_aware_non_utc_and_naive_device_timestamps_are_stored_as_utc_or_null(env: Env) -> None:
    from datetime import timezone

    plus = timezone(timedelta(hours=5, minutes=30))
    session_id = env.open()
    aware = datetime(2026, 1, 1, 17, 31, tzinfo=plus)  # 12:01 UTC
    naive = datetime(2026, 1, 1, 12, 2, 0)
    env.service.ingest(session_id, sample(15, device_timestamp=aware))
    env.service.ingest(session_id, sample(15, seconds=1, device_timestamp=naive))
    first, second = env.samples(session_id)
    assert first.device_timestamp is not None
    assert first.device_timestamp.replace(tzinfo=UTC) == T0 + timedelta(minutes=1)
    assert second.device_timestamp is None  # the naive value represents no instant
    flagged = {a.sample_id: a.reasons for a in env.per_sample(session_id)}
    assert flagged[second.id] == ["invalid_timestamp"]


@pytest.mark.parametrize(
    "case",
    ["unknown", "sensor", "source_kind", "is_synthetic"],
)
def test_delivery_contract_violations_write_nothing_and_move_no_state(env: Env, case: str) -> None:
    real = case == "is_synthetic"
    session_id = env.open(
        source_kind=SourceKind.REAL if real else SourceKind.SIMULATED, is_synthetic=not real
    )
    env.service.ingest(session_id, _sample_for(real))  # sequence 1, establishes state

    target = session_id
    bad: HeartRateSample
    if case == "unknown":
        target, bad = uuid.UUID(int=999), _sample_for(real)
    elif case == "sensor":
        bad = HeartRateSample(
            sensor_id=OTHER_SENSOR_ID,
            source_kind=SourceKind.SIMULATED,
            is_synthetic=True,
            received_hr=15.0,
            received_at=T0 + timedelta(seconds=1),
        )
    elif case == "source_kind":
        bad = HeartRateSample(
            sensor_id=SENSOR_ID,
            source_kind=SourceKind.MANUAL,
            is_synthetic=True,
            received_hr=15.0,
            received_at=T0 + timedelta(seconds=1),
        )
    else:  # a real session, but the sample claims to be synthetic
        bad = HeartRateSample(
            sensor_id=SENSOR_ID,
            source_kind=SourceKind.REAL,
            is_synthetic=True,
            received_hr=15.0,
            received_at=T0 + timedelta(seconds=1),
        )
    before = (env.count(SensorSample), env.count(SignalAssessment))
    ids_before = env.ids.new_id().int  # consuming one id is harmless; compare afterwards
    with pytest.raises(InvalidSensorSample) as caught:
        env.service.ingest(target, bad)
    assert caught.value.code == "invalid_sensor_sample"
    assert (env.count(SensorSample), env.count(SignalAssessment)) == before
    assert env.ids.new_id().int == ids_before + 1  # a rejected delivery consumed no id

    follow_up = env.service.ingest(session_id, _sample_for(real, seconds=1))
    assert follow_up.sequence == 2  # the sequence did not move
    assert [r.sequence for r in env.samples(session_id)] == [1, 2]


def _sample_for(real: bool, seconds: float = 0.0) -> HeartRateSample:
    return HeartRateSample(
        sensor_id=SENSOR_ID,
        source_kind=SourceKind.REAL if real else SourceKind.SIMULATED,
        is_synthetic=not real,
        received_hr=15.0,
        received_at=T0 + timedelta(seconds=seconds),
    )


def test_closed_and_repeated_close_are_rejected_deterministically(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15))
    env.service.close(session_id)
    with pytest.raises(InvalidSensorSample) as late:
        env.service.ingest(session_id, sample(15, seconds=1))
    assert late.value.details["reason"] == "closed"
    with pytest.raises(InvalidSensorSample) as again:
        env.service.close(session_id)
    assert again.value.details["reason"] == "closed"
    with pytest.raises(InvalidSensorSample) as unknown:
        env.service.close(uuid.UUID(int=999))
    assert unknown.value.details["reason"] == "unknown_or_inactive"
    assert len(env.samples(session_id)) == 1


def test_a_huge_int_value_is_rejected_before_any_write(env: Env) -> None:
    session_id = env.open()
    before = (env.count(SensorSample), env.count(SignalAssessment))
    with pytest.raises(ValueError, match="outside the range of a float"):
        env.service.ingest(session_id, sample(10**400))
    assert (env.count(SensorSample), env.count(SignalAssessment)) == before
    assert env.service.ingest(session_id, sample(15)).sequence == 1


# --- raw-first durability ------------------------------------------------------------------


def test_a_failed_assessment_leaves_a_durable_unassessed_raw_sample(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = env.open()
    monkeypatch.setattr(repositories, "insert_signal_assessment", boom)
    with pytest.raises(RuntimeError, match="injected"):
        env.service.ingest(session_id, sample(15))
    assert len(env.samples(session_id)) == 1  # transaction 1 was committed
    assert env.assessments(session_id) == []  # nothing fabricated, nothing marked GOOD
    monkeypatch.undo()

    # Sequence 1 is spent; the stream state did not move, so the next sample is assessed as the
    # first of its stream (no gap and no timestamp finding against the unassessed one).
    result = env.service.ingest(session_id, sample(15, seconds=100))
    assert result.sequence == 2 and result.gap is None
    assert [r.sequence for r in env.samples(session_id)] == [1, 2]
    (only,) = env.per_sample(session_id)
    assert only.sample_id == result.sample_id and env.ranges(session_id) == []


def test_a_failed_raw_insert_spends_no_sequence_and_writes_nothing(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = env.open()
    monkeypatch.setattr(repositories, "insert_raw_sample", boom)
    with pytest.raises(RuntimeError, match="injected"):
        env.service.ingest(session_id, sample(15))
    monkeypatch.undo()
    assert env.samples(session_id) == [] and env.assessments(session_id) == []
    assert env.service.ingest(session_id, sample(15)).sequence == 1


def test_a_failed_second_write_rolls_back_the_whole_assessment_transaction(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The gap row is written after the per-sample row; if it fails neither is kept."""
    session_id = env.open()
    env.service.ingest(session_id, sample(15))
    original = repositories.insert_signal_assessment
    calls = {"n": 0}

    def second_call_fails(db: Session, **values: Any) -> SignalAssessment:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("injected failure")
        return original(db, **values)

    monkeypatch.setattr(repositories, "insert_signal_assessment", second_call_fails)
    with pytest.raises(RuntimeError, match="injected"):
        env.service.ingest(session_id, sample(15, seconds=60))  # would produce a gap
    monkeypatch.undo()
    assert len(env.per_sample(session_id)) == 1 and env.ranges(session_id) == []
    assert len(env.samples(session_id)) == 2


# --- assessments ---------------------------------------------------------------------------


def test_assessments_point_at_their_sample_session_and_run(env: Env) -> None:
    session_id = env.open()
    first = env.service.ingest(session_id, sample(15))
    second = env.service.ingest(session_id, sample(15, seconds=1))
    run_id = env.run_id(session_id)
    rows = env.per_sample(session_id)
    assert [r.sample_id for r in rows] == [first.sample_id, second.sample_id]
    assert all(r.processing_run_id == run_id for r in rows)
    assert all(r.recording_session_id == session_id for r in rows)
    assert all(r.range_start_at is None and r.after_sample_id is None for r in rows)
    assert [r.quality_state for r in rows] == ["GOOD", "GOOD"] and rows[0].reasons == []


@pytest.mark.parametrize(
    ("value", "payload", "reason"),
    [
        (None, b"junk", "malformed_sample"),
        (None, None, "missing"),
        (math.nan, None, "malformed_sample"),
        (math.inf, b"p", "malformed_sample"),
        (-math.inf, None, "malformed_sample"),
        (25.0, None, "impossible_hr"),
        (5.0, None, "impossible_hr"),
    ],
)
def test_invalid_samples_are_persisted_and_assessed_invalid(
    env: Env, value: float | None, payload: bytes | None, reason: str
) -> None:
    session_id = env.open()
    result = env.service.ingest(session_id, sample(value, raw_payload=payload))
    assert len(env.samples(session_id)) == 1
    (row,) = env.per_sample(session_id)
    assert row.sample_id == result.sample_id
    assert row.quality_state == QualityState.INVALID.value and row.reasons == [reason]


def test_duplicate_out_of_order_and_jump_findings_are_stored(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(11, seconds=10))
    env.service.ingest(session_id, sample(11, seconds=10))  # same receive time
    env.service.ingest(session_id, sample(11, seconds=9))  # earlier than the previous
    env.service.ingest(session_id, sample(17, seconds=10.5))  # |17 - 11| > 5
    states = [(r.quality_state, r.reasons) for r in env.per_sample(session_id)]
    assert states == [
        ("GOOD", []),
        ("POOR", ["duplicate_timestamp"]),
        ("POOR", ["out_of_order_timestamp"]),
        ("POOR", ["implausible_jump"]),
    ]


def test_a_gap_is_stored_as_a_closed_range_between_the_two_samples(env: Env) -> None:
    session_id = env.open()
    first = env.service.ingest(session_id, sample(15, seconds=0))
    second = env.service.ingest(session_id, sample(15, seconds=8))  # > gap_after_seconds (7)
    assert second.gap is not None
    (gap,) = env.ranges(session_id)
    assert gap.quality_state == QualityState.MISSING.value and gap.reasons == ["gap"]
    assert gap.sample_id is None and gap.processing_run_id == env.run_id(session_id)
    assert gap.range_start_at is not None and gap.range_end_at is not None
    assert gap.range_start_at.replace(tzinfo=UTC) == T0
    assert gap.range_end_at.replace(tzinfo=UTC) == T0 + timedelta(seconds=8)
    assert gap.after_sample_id == first.sample_id and gap.before_sample_id == second.sample_id
    assert len(env.per_sample(session_id)) == 2


def test_no_gap_at_exactly_the_configured_limit(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=0))
    env.service.ingest(session_id, sample(15, seconds=7))
    assert env.ranges(session_id) == []


def test_an_invalid_arrival_still_counts_for_the_gap_reference(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=0))
    invalid = env.service.ingest(session_id, sample(None, seconds=5))
    env.service.ingest(session_id, sample(15, seconds=10))  # 5 s after the invalid arrival
    assert env.ranges(session_id) == []
    assert invalid.assessment.state is QualityState.INVALID


# --- close ---------------------------------------------------------------------------------


def test_close_stores_a_due_stale_range_and_ends_the_session(env: Env, clock: ManualClock) -> None:
    session_id = env.open()
    first = env.service.ingest(session_id, sample(15, seconds=0))
    clock.advance(10)  # > stale_after_seconds (3.5)
    env.service.close(session_id)
    (stale,) = env.ranges(session_id)
    assert stale.quality_state == QualityState.STALE.value and stale.reasons == ["stale"]
    assert stale.range_start_at is not None and stale.range_end_at is not None
    assert stale.range_start_at.replace(tzinfo=UTC) == T0
    assert stale.range_end_at.replace(tzinfo=UTC) == T0 + timedelta(seconds=10)
    assert stale.after_sample_id == first.sample_id and stale.before_sample_id is None
    row = env.session_row(session_id)
    assert row.ended_at is not None
    assert row.ended_at.replace(tzinfo=UTC) == T0 + timedelta(seconds=10)
    assert row.end_reason == CLOSE_END_REASON == "completed"


def test_stale_reference_is_the_maximum_receive_time(env: Env, clock: ManualClock) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=20))
    env.service.ingest(session_id, sample(15, seconds=1))  # later arrival, older receive time
    clock.advance(21)  # now = T0 + 21: age of the maximum (20) is 1 s, not stale
    env.service.close(session_id)
    assert env.ranges(session_id) == []


def test_close_without_a_due_stale_range_or_samples_only_ends_the_session(
    env: Env, clock: ManualClock
) -> None:
    recent = env.open()
    env.service.ingest(recent, sample(15, seconds=0))
    clock.advance(3.5)  # exactly the limit: not stale
    env.service.close(recent)
    assert env.ranges(recent) == []
    assert env.session_row(recent).end_reason == "completed"

    empty = env.open(config=make_config(config_version="2"))
    env.service.close(empty)
    assert env.assessments(empty) == [] and env.session_row(empty).ended_at is not None


def test_a_failed_close_leaves_the_session_open(
    env: Env, clock: ManualClock, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15))
    clock.advance(10)
    monkeypatch.setattr(repositories, "close_recording_session", boom)
    with pytest.raises(RuntimeError, match="injected"):
        env.service.close(session_id)
    monkeypatch.undo()
    assert env.session_row(session_id).ended_at is None
    assert env.ranges(session_id) == []  # the stale row was rolled back with it
    assert env.service.ingest(session_id, sample(15, seconds=11)).sequence == 2
    env.service.close(session_id)  # and a retry works
    assert env.session_row(session_id).end_reason == "completed"


# --- append-only repositories and verification ---------------------------------------------


def test_repositories_expose_no_update_or_delete_for_raw_samples_or_assessments() -> None:
    public = [n for n in dir(repositories) if not n.startswith("_")]
    names = [n for n in public if callable(getattr(repositories, n))]
    assert not [n for n in names if n.startswith(("update", "delete", "remove", "merge"))]
    mutating = [n for n in names if n.startswith(("insert", "close"))]
    assert sorted(mutating) == [
        "close_recording_session",
        "insert_processing_run",
        "insert_raw_sample",
        "insert_recording_session",
        "insert_signal_assessment",
    ]


def test_ingestion_never_modifies_stored_rows(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=0))
    snapshot = _snapshot(env, session_id)
    env.service.ingest(session_id, sample(15, seconds=8))
    env.service.close(session_id)
    after = _snapshot(env, session_id)
    assert after[0][: len(snapshot[0])] == snapshot[0]  # the first raw row is unchanged
    assert snapshot[1][0] in after[1]  # and so is its assessment
    assert len(after[0]) == 2


Rows = list[tuple[Any, ...]]


def _snapshot(env: Env, session_id: uuid.UUID) -> tuple[Rows, Rows]:
    raw = [
        (r.id, r.sequence, r.received_hr, r.received_hr_nonfinite, r.received_at, r.elapsed_seconds)
        for r in env.samples(session_id)
    ]
    assessed = [
        (a.id, a.sample_id, a.quality_state, tuple(a.reasons), a.created_at)
        for a in env.assessments(session_id)
    ]
    return raw, assessed


def test_refolding_the_stored_rows_reproduces_the_stored_assessments(
    env: Env, clock: ManualClock
) -> None:
    """Verification: rebuild every sample from its row and replay the signal core."""
    session_id = env.open()
    config = make_config()
    inputs: list[Callable[[], HeartRateSample]] = [
        lambda: sample(15, seconds=0),
        lambda: sample(15, seconds=0),  # duplicate
        lambda: sample(None, seconds=2, raw_payload=b"x"),
        lambda: sample(math.nan, seconds=3),
        lambda: sample(17, seconds=12),  # gap
        lambda: sample(11, seconds=11),  # out of order and a jump
        lambda: sample(30, seconds=13),
        lambda: sample(math.inf, seconds=14, device_timestamp=T0 + timedelta(seconds=14)),
        lambda: sample(15, seconds=15, device_timestamp=T0 + timedelta(seconds=15)),
    ]
    for make in inputs:
        env.service.ingest(session_id, make())

    state = StreamState()
    expected: list[tuple[str, list[str]]] = []
    expected_gaps: list[tuple[datetime, datetime]] = []
    for row in env.samples(session_id):
        step = assess_sample(sample_from_row(row, sensor_id=SENSOR_ID), state, config)
        state = step.next_state
        expected.append((step.assessment.state.value, [r.value for r in step.assessment.reasons]))
        if step.gap is not None:
            expected_gaps.append((step.gap.start, step.gap.end))
    stored = [(a.quality_state, a.reasons) for a in env.per_sample(session_id)]
    assert stored == expected
    stored_gaps = [
        (a.range_start_at.replace(tzinfo=UTC), a.range_end_at.replace(tzinfo=UTC))
        for a in env.ranges(session_id)
        if a.range_start_at is not None and a.range_end_at is not None
    ]
    assert stored_gaps == expected_gaps and expected_gaps


# --- an unassessed sample restarts the stream comparison ----------------------------------


def _fail_next_assessment(
    env: Env, session_id: uuid.UUID, hr: float | None, seconds: float
) -> None:
    """Commit a raw sample whose assessment transaction fails."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(repositories, "insert_signal_assessment", boom)
        with pytest.raises(RuntimeError, match="injected"):
            env.service.ingest(session_id, sample(hr, seconds=seconds))


def test_no_false_gap_across_an_unassessed_sample(env: Env) -> None:
    """A@0 assessed, B@5 raw only, C@10: neither real interval exceeds the 7 s limit."""
    session_id = env.open()
    a = env.service.ingest(session_id, sample(15, seconds=0))
    _fail_next_assessment(env, session_id, 15, 5)
    c = env.service.ingest(session_id, sample(15, seconds=10))
    assert c.gap is None and env.ranges(session_id) == []
    rows = env.samples(session_id)
    assert [r.sequence for r in rows] == [1, 2, 3] and rows[0].id == a.sample_id
    assert [x.sample_id for x in env.per_sample(session_id)] == [a.sample_id, c.sample_id]
    assert rows[1].id not in {x.sample_id for x in env.assessments(session_id)}  # B stays raw-only


def test_consecutive_failures_keep_the_restart_until_one_succeeds(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=0))
    _fail_next_assessment(env, session_id, 15, 5)
    _fail_next_assessment(env, session_id, 15, 10)
    c = env.service.ingest(session_id, sample(15, seconds=15))
    assert c.gap is None and env.ranges(session_id) == []
    assert len(env.samples(session_id)) == 4 and len(env.per_sample(session_id)) == 2


def test_the_stream_resumes_normal_checks_after_the_next_assessed_sample(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=0))
    _fail_next_assessment(env, session_id, 15, 5)
    c = env.service.ingest(session_id, sample(15, seconds=10))
    d = env.service.ingest(session_id, sample(15, seconds=10))  # duplicate of C: checked again
    e = env.service.ingest(session_id, sample(15, seconds=20))  # 10 s after D: a real gap
    assert d.assessment.reasons[0].value == "duplicate_timestamp"
    assert e.gap is not None and e.gap.start == T0 + timedelta(seconds=10)
    (gap,) = env.ranges(session_id)
    assert gap.after_sample_id == d.sample_id and gap.before_sample_id == e.sample_id
    assert c.sample_id != d.sample_id


def test_no_timestamp_or_jump_finding_is_taken_against_a_non_adjacent_sample(env: Env) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(11, seconds=5))
    _fail_next_assessment(env, session_id, 11, 6)
    # Against A this would be out of order (earlier time) and a jump (|17 - 11| > 5); the
    # sample between them is unassessed, so neither conclusion is drawn.
    c = env.service.ingest(session_id, sample(17, seconds=3))
    assert c.assessment.state is QualityState.GOOD and c.assessment.reasons == ()


def test_the_stale_reference_includes_an_unassessed_latest_sample(
    env: Env, clock: ManualClock
) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=0))
    _fail_next_assessment(env, session_id, 15, 5)
    b_id = env.samples(session_id)[1].id
    clock.advance(10)  # 5 s after B: stale; 10 s after A would be the wrong start
    env.service.close(session_id)
    (stale,) = env.ranges(session_id)
    assert stale.range_start_at is not None
    assert stale.range_start_at.replace(tzinfo=UTC) == T0 + timedelta(seconds=5)
    assert stale.after_sample_id == b_id and stale.before_sample_id is None


def test_the_maximum_receive_time_survives_a_restart(env: Env, clock: ManualClock) -> None:
    session_id = env.open()
    env.service.ingest(session_id, sample(15, seconds=20))
    _fail_next_assessment(env, session_id, 15, 1)
    env.service.ingest(session_id, sample(15, seconds=2))
    clock.advance(21)  # the maximum receive time is 20: 1 s old, not stale
    env.service.close(session_id)
    assert env.ranges(session_id) == []
