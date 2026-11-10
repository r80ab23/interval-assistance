"""Replay uses migrated isolated SQLite and deterministic clocks/IDs; no physiological claims."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from interval_assistance.core.clock import ManualClock
from interval_assistance.ingestion.replay import (
    REPLAY_IDENTIFIER,
    ReplayCancelled,
    ReplayError,
    ReplayService,
)
from interval_assistance.storage import repositories
from interval_assistance.storage.alembic_helpers import make_alembic_config
from interval_assistance.storage.engine import create_db_engine
from interval_assistance.storage.models import (
    RecordingSession,
    Sensor,
    SensorSample,
    SignalAssessment,
)
from tests.integration.test_ingestion import Env, boom
from tests.unit.signal.helpers import T0, make_config, sample


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    url = f"sqlite:///{tmp_path / 'replay.db'}"
    command.upgrade(make_alembic_config(url), "head")
    engine: Engine = create_db_engine(url)
    yield Env(engine, ManualClock(T0))
    engine.dispose()


def origin(env: Env, *, empty: bool = False) -> uuid.UUID:
    session = env.open()
    if not empty:
        for index, value in enumerate(
            (11.0, 17.0, None, float("nan"), float("inf"), -float("inf"))
        ):
            assert isinstance(env.clock, ManualClock)
            if index:
                env.clock.advance(5)
            env.service.ingest(session, sample(value, seconds=index * 5, raw_payload=b"raw"))
    env.service.close(session)
    return session


@pytest.mark.asyncio
async def test_repeatability_pacing_provenance_and_explicit_close(env: Env) -> None:
    source = origin(env)
    originals = [
        (r.id, r.received_hr, r.received_hr_nonfinite, r.raw_payload) for r in env.samples(source)
    ]
    results: list[list[tuple[object, ...]]] = []
    findings: list[list[tuple[str, object]]] = []
    sensors: list[uuid.UUID] = []
    for speed in (1, 5, 20):
        pauses: list[float] = []

        async def sleep(delay: float, captured: list[float] = pauses) -> None:
            captured.append(delay)

        execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
            source,
            config=make_config(),
            logical_start_utc=T0,
            close_elapsed_seconds=30,
            speed=speed,
        )
        destination = execution.opened.session_id
        await execution.run_samples()
        assert not execution.completed
        assert env.session_row(destination).ended_at is None
        execution.close()
        assert execution.completed
        rows = env.samples(destination)
        assert [r.origin_sample_id for r in rows] == [r[0] for r in originals]
        assert [r.sequence for r in rows] == list(range(1, 7))
        assert pauses == [0] + [5 / speed] * 5
        assert all(r.source_kind == "replay" and r.is_synthetic for r in rows)
        results.append(
            [
                (
                    r.received_hr,
                    r.received_hr_nonfinite,
                    r.received_at,
                    r.ingestion_timestamp,
                    r.elapsed_seconds,
                    r.raw_payload,
                )
                for r in rows
            ]
        )
        assert env.session_row(destination).origin_recording_session_id == source
        assert execution.opened.processing_run_id != env.run_id(source)
        sensors.append(env.session_row(destination).sensor_id)
        findings.append([(a.quality_state, a.reasons) for a in env.per_sample(destination)])
        with pytest.raises(ReplayError):
            await execution.run_samples()
    assert results[0] == results[1] == results[2]
    assert findings[0] == findings[1] == findings[2]
    assert len(set(sensors)) == 1
    assert originals == [
        (r.id, r.received_hr, r.received_hr_nonfinite, r.raw_payload) for r in env.samples(source)
    ]


@pytest.mark.asyncio
async def test_empty_and_replay_of_replay(env: Env) -> None:
    source = origin(env, empty=True)
    for _ in range(2):
        execution = ReplayService(env.factory, env.ids).open(
            source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=0, speed=1
        )
        await execution.run_samples()
        execution.close()
        assert env.samples(execution.opened.session_id) == []
        assert env.assessments(execution.opened.session_id) == []
        assert env.session_row(execution.opened.session_id).origin_recording_session_id == source
        source = execution.opened.session_id


@pytest.mark.parametrize("case", ["open", "speed", "close", "naive", "elapsed", "sequence"])
def test_preflight_writes_nothing(env: Env, case: str) -> None:
    source = env.open() if case == "open" else origin(env)
    if case in ("elapsed", "sequence"):
        with env.factory() as db, db.begin():
            row = db.scalars(
                select(SensorSample)
                .where(SensorSample.recording_session_id == source)
                .order_by(SensorSample.sequence)
            ).first()
            assert row is not None
            if case == "elapsed":
                row.elapsed_seconds = 100
            else:
                row.sequence = 100
    before = (env.count(Sensor), env.count(RecordingSession))
    with pytest.raises(ReplayError, match="preflight"):
        ReplayService(env.factory, env.ids).open(
            source,
            config=make_config(),
            logical_start_utc=T0.replace(tzinfo=None) if case == "naive" else T0,
            close_elapsed_seconds=0 if case == "close" else 30,
            speed=0 if case == "speed" else 1,
        )
    assert before == (env.count(Sensor), env.count(RecordingSession))


@pytest.mark.parametrize("matches", [0, 1, 2])
def test_registry_exact_identity(env: Env, matches: int) -> None:
    source = origin(env, empty=True)
    with env.factory() as db, db.begin():
        repositories.insert_sensor(db, id=env.ids.new_id(), kind="replay", created_at=T0)
        for _ in range(matches):
            repositories.insert_sensor(
                db,
                id=env.ids.new_id(),
                kind="replay",
                created_at=T0,
                external_identifier=REPLAY_IDENTIFIER,
            )
    before = env.count(Sensor)
    if matches == 2:
        with pytest.raises(ReplayError, match="ambiguous_identity"):
            ReplayService(env.factory, env.ids).open(
                source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=0, speed=1
            )
    else:
        ReplayService(env.factory, env.ids).open(
            source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=0, speed=1
        )
    assert env.count(Sensor) == before + (matches == 0)


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["raw", "assessment", "pacing", "cancel", "close"])
async def test_failures_leave_open_destination_and_stop(
    env: Env, monkeypatch: pytest.MonkeyPatch, stage: str
) -> None:
    source = origin(env)

    async def sleep(delay: float) -> None:
        if stage == "pacing":
            raise RuntimeError("secret payload")
        if stage == "cancel":
            raise asyncio.CancelledError("secret payload")

    execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
        source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=30, speed=1
    )
    if stage in ("raw", "assessment"):
        monkeypatch.setattr(
            repositories,
            "insert_raw_sample" if stage == "raw" else "insert_signal_assessment",
            boom,
        )
    if stage == "close":
        await execution.run_samples()
        monkeypatch.setattr(repositories, "close_recording_session", boom)
        with pytest.raises(ReplayError):
            execution.close()
    else:
        with pytest.raises((ReplayError, ReplayCancelled)) as error:
            await execution.run_samples()
        assert "secret" not in str(error.value)
        assert isinstance(error.value, ReplayError | ReplayCancelled)
        assert error.value.destination_id == execution.opened.session_id
        assert len(env.samples(execution.opened.session_id)) == (1 if stage == "assessment" else 0)
        assert env.assessments(execution.opened.session_id) == []
    assert env.session_row(execution.opened.session_id).ended_at is None
    assert not execution.completed
    with pytest.raises(ReplayError):
        await execution.run_samples()
    with pytest.raises(ReplayError):
        execution.close()


@pytest.mark.asyncio
async def test_fixture_generator_ingestion_replay(env: Env) -> None:
    import json
    from itertools import islice

    from interval_assistance.ingestion.replay_fixture import stream_hash
    from interval_assistance.sensors.simulator import SimulatorConfig, generate_values

    fixture = Path(__file__).resolve().parents[2] / "data/synthetic/replay-basic.fixture.json"
    metadata = json.loads(fixture.read_text())
    config = SimulatorConfig(**metadata["parameters"])
    generated = [
        sample(v, seconds=i * config.interval_seconds)
        for i, v in enumerate(islice(generate_values(config), metadata["sample_count"]))
    ]
    assert stream_hash(generated) == metadata["stream_sha256"]
    source = env.open()
    assert isinstance(env.clock, ManualClock)
    for i, item in enumerate(generated):
        if i:
            env.clock.advance(config.interval_seconds)
        env.service.ingest(source, item)
    env.service.close(source)

    async def sleep(delay: float) -> None:
        pass

    execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
        source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=5, speed=20
    )
    await execution.run_samples()
    execution.close()
    assert [(a.quality_state, a.reasons) for a in env.per_sample(source)] == [
        (a.quality_state, a.reasons) for a in env.per_sample(execution.opened.session_id)
    ]


@pytest.mark.asyncio
async def test_unassessed_origin_is_freshly_assessed_and_not_modified(
    env: Env, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = env.open()
    with monkeypatch.context() as patch:
        patch.setattr(repositories, "insert_signal_assessment", boom)
        with pytest.raises(RuntimeError):
            env.service.ingest(source, sample())
    env.service.close(source)

    async def sleep(delay: float) -> None:
        pass

    execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
        source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=0, speed=1
    )
    await execution.run_samples()
    execution.close()
    assert env.assessments(source) == []
    assert len(env.per_sample(execution.opened.session_id)) == 1


@pytest.mark.parametrize("operation", ["insert_sensor", "insert_processing_run"])
def test_open_failures_rollback_destination(
    env: Env, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    source = origin(env, empty=True)
    before = env.count(RecordingSession)
    monkeypatch.setattr(repositories, operation, boom)
    with pytest.raises(ReplayError):
        ReplayService(env.factory, env.ids).open(
            source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=0, speed=1
        )
    assert env.count(RecordingSession) == before


@pytest.mark.asyncio
async def test_original_time_order_and_synthetic_flag_are_preserved(env: Env) -> None:
    from dataclasses import replace
    from datetime import timedelta

    from interval_assistance.sensors.sample import SourceKind

    source = env.open(source_kind=SourceKind.REAL, is_synthetic=False)
    assert isinstance(env.clock, ManualClock)
    for i, seconds in enumerate((2, 2, 0)):
        if i:
            env.clock.advance(1)
        item = replace(
            sample(11 + i * 3, seconds=seconds),
            source_kind=SourceKind.REAL,
            is_synthetic=False,
            device_timestamp=T0 + timedelta(seconds=seconds),
        )
        env.service.ingest(source, item)
    env.service.close(source)

    async def sleep(delay: float) -> None:
        pass

    execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
        source, config=make_config(), logical_start_utc=T0, close_elapsed_seconds=6, speed=5
    )
    await execution.run_samples()
    execution.close()
    rows = env.samples(execution.opened.session_id)
    assert all(not r.is_synthetic for r in rows)
    assert [r.received_at for r in rows] == [r.received_at for r in env.samples(source)]
    findings = [a.reasons for a in env.per_sample(execution.opened.session_id)]
    assert "duplicate_timestamp" in findings[1]
    assert "out_of_order_timestamp" in findings[2]
    assert any("stale" in a.reasons for a in env.ranges(execution.opened.session_id))


@pytest.mark.asyncio
@pytest.mark.parametrize("close_offset,stale", [(10.5, False), (10.500001, True)])
async def test_equal_elapsed_gap_and_stale_boundary(
    env: Env, close_offset: float, stale: bool
) -> None:
    from datetime import timedelta, timezone

    source = env.open()
    env.service.ingest(source, sample(11))
    # Equal elapsed offsets are permitted; receive time alone drives gap detection.
    env.service.ingest(source, sample(12, seconds=7))
    assert isinstance(env.clock, ManualClock)
    env.clock.advance(7)
    env.service.close(source)
    pauses: list[float] = []

    async def sleep(delay: float) -> None:
        pauses.append(delay)

    execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
        source,
        config=make_config(),
        logical_start_utc=T0.astimezone(timezone(timedelta(hours=3))),
        close_elapsed_seconds=close_offset,
        speed=5,
    )
    await execution.run_samples()
    execution.close()
    assert pauses == [0, 0]
    assert [r.elapsed_seconds for r in env.samples(execution.opened.session_id)] == [0, 0]
    ranges = env.ranges(execution.opened.session_id)
    assert not any("gap" in a.reasons for a in ranges)
    assert any("stale" in a.reasons for a in ranges) is stale


@pytest.mark.asyncio
async def test_failure_after_committed_progress(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    source = origin(env)
    original_insert = repositories.insert_signal_assessment
    calls = 0

    def fail_third(db: Session, **values: Any) -> SignalAssessment:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("injected assessment failure")
        return original_insert(db, **values)

    async def sleep(delay: float) -> None:
        pass

    execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
        source,
        config=make_config(),
        logical_start_utc=T0,
        close_elapsed_seconds=30,
        speed=5,
    )
    monkeypatch.setattr(repositories, "insert_signal_assessment", fail_third)
    with pytest.raises(ReplayError) as error:
        await execution.run_samples()
    destination = execution.opened.session_id
    rows = env.samples(destination)
    assert [row.sequence for row in rows] == [1, 2, 3]
    assert [a.sample_id for a in env.per_sample(destination)] == [r.id for r in rows[:2]]
    assert error.value.origin_sample_id == env.samples(source)[2].id
    assert error.value.destination_id == destination
    assert env.session_row(destination).ended_at is None
    with pytest.raises(ReplayError):
        await execution.run_samples()
    assert len(env.samples(destination)) == 3


@pytest.mark.asyncio
async def test_nonempty_replay_chain_links_immediate_origin(env: Env) -> None:
    source = origin(env)

    async def sleep(delay: float) -> None:
        pass

    for _ in range(2):
        before = [
            (r.id, r.received_hr, r.received_hr_nonfinite, r.raw_payload)
            for r in env.samples(source)
        ]
        execution = ReplayService(env.factory, env.ids, sleep=sleep).open(
            source,
            config=make_config(),
            logical_start_utc=T0,
            close_elapsed_seconds=30,
            speed=20,
        )
        await execution.run_samples()
        execution.close()
        destination = execution.opened.session_id
        rows = env.samples(destination)
        assert [r.origin_sample_id for r in rows] == [r[0] for r in before]
        assert [(r.received_hr, r.received_hr_nonfinite, r.raw_payload) for r in rows] == [
            r[1:] for r in before
        ]
        assert not {r.id for r in rows} & {r[0] for r in before}
        assert env.session_row(destination).origin_recording_session_id == source
        assert execution.opened.processing_run_id != env.run_id(source)
        assert before == [
            (r.id, r.received_hr, r.received_hr_nonfinite, r.raw_payload)
            for r in env.samples(source)
        ]
        source = destination
