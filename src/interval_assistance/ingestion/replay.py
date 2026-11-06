"""Closed recording replay with explicit logical time and explicit completion.

One writer per execution; registry access is serialized within this process only.
"""

from __future__ import annotations

import asyncio
import math
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from threading import Lock

from sqlalchemy.orm import Session, sessionmaker

from interval_assistance.core.clock import Clock
from interval_assistance.core.ids import IdGenerator
from interval_assistance.ingestion.mapping import sample_from_row, to_utc
from interval_assistance.ingestion.service import IngestionService, OpenedSession
from interval_assistance.sensors.sample import HeartRateSample, SourceKind
from interval_assistance.signal import SignalQualityConfig, check_identity
from interval_assistance.storage import repositories

REPLAY_IDENTIFIER = "interval-assistance.replay"
_REGISTRY_LOCK = Lock()
Sleep = Callable[[float], Awaitable[None]]


class ReplayError(Exception):
    """Safe context only; never include the underlying exception or raw values."""

    def __init__(
        self,
        stage: str,
        destination_id: uuid.UUID | None = None,
        origin_sample_id: uuid.UUID | None = None,
    ) -> None:
        self.stage = stage
        self.destination_id = destination_id
        self.origin_sample_id = origin_sample_id
        super().__init__(f"replay failed at {stage}")


class ReplayCancelled(asyncio.CancelledError):
    def __init__(self, destination_id: uuid.UUID, origin_sample_id: uuid.UUID | None) -> None:
        self.destination_id = destination_id
        self.origin_sample_id = origin_sample_id
        self.stage = "pacing"
        super().__init__("replay cancelled")


class _ReplayClock(Clock):
    def __init__(self, start: datetime) -> None:
        self.start = start
        self.elapsed = 0.0

    def now_utc(self) -> datetime:
        return self.start + timedelta(seconds=self.elapsed)

    def monotonic(self) -> float:
        return self.elapsed

    def move_to(self, elapsed: float) -> None:
        if elapsed < self.elapsed:
            raise ValueError("logical time cannot regress")
        self.elapsed = elapsed


@dataclass(frozen=True)
class _Input:
    origin_id: uuid.UUID
    elapsed: float
    sample: HeartRateSample


def _number(value: float, *, positive: bool = False) -> float:
    if isinstance(value, bool):
        raise ValueError("invalid replay number")
    result = float(value)
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        raise ValueError("invalid replay number")
    return result


class ReplayExecution:
    """Run once, then close explicitly. Any failure makes this execution terminal."""

    def __init__(
        self,
        opened: OpenedSession,
        service: IngestionService,
        clock: _ReplayClock,
        inputs: tuple[_Input, ...],
        close_elapsed: float,
        speed: float,
        sleep: Sleep,
    ) -> None:
        self.opened = opened
        self._service = service
        self._clock = clock
        self._inputs = inputs
        self._close_elapsed = close_elapsed
        self._speed = speed
        self._sleep = sleep
        self._state = "ready"

    async def run_samples(self) -> None:
        if self._state != "ready":
            raise ReplayError("lifecycle", self.opened.session_id)
        self._state = "running"
        previous = 0.0
        current: uuid.UUID | None = None
        stage = "pacing"
        try:
            for item in self._inputs:
                current = item.origin_id
                stage = "pacing"
                await self._sleep((item.elapsed - previous) / self._speed)
                self._clock.move_to(item.elapsed)
                stage = "ingestion"
                self._service._ingest(
                    self.opened.session_id,
                    item.sample,
                    origin_sample_id=item.origin_id,
                )
                previous = item.elapsed
        except asyncio.CancelledError:
            self._state = "failed"
            raise ReplayCancelled(self.opened.session_id, current) from None
        except Exception:
            self._state = "failed"
            raise ReplayError(stage, self.opened.session_id, current) from None
        self._state = "awaiting_close"

    def close(self) -> None:
        if self._state != "awaiting_close":
            raise ReplayError("lifecycle", self.opened.session_id)
        try:
            self._clock.move_to(self._close_elapsed)
            self._service.close(self.opened.session_id)
        except Exception:
            self._state = "failed"
            raise ReplayError("close", self.opened.session_id) from None
        self._state = "completed"

    @property
    def completed(self) -> bool:
        return self._state == "completed"


class ReplayService:
    def __init__(
        self, factory: sessionmaker[Session], ids: IdGenerator, *, sleep: Sleep = asyncio.sleep
    ) -> None:
        self._factory = factory
        self._ids = ids
        self._sleep = sleep

    def open(
        self,
        origin_session_id: uuid.UUID,
        *,
        config: SignalQualityConfig,
        logical_start_utc: datetime,
        close_elapsed_seconds: float,
        speed: float,
    ) -> ReplayExecution:
        stage = "preflight"
        current: uuid.UUID | None = None
        try:
            if logical_start_utc.utcoffset() is None:
                raise ValueError("logical start must be aware")
            start = to_utc(logical_start_utc)
            close_elapsed = _number(close_elapsed_seconds)
            pacing = _number(speed, positive=True)
            end = start + timedelta(seconds=close_elapsed)
            inputs = []
            with self._factory() as db, db.begin():
                origin = repositories.get_recording_session(db, origin_session_id)
                if (
                    origin is None
                    or origin.ended_at is None
                    or origin.end_reason
                    not in {
                        "completed",
                        "interrupted",
                    }
                ):
                    raise ValueError("origin must be closed")
                synthetic = origin.is_synthetic
                check_identity(
                    config,
                    repositories.find_config_hash(
                        db,
                        config.config_id,
                        config.config_version,
                    ),
                )
                previous = 0.0
                for sequence, row in enumerate(
                    repositories.list_raw_samples(
                        db,
                        origin_session_id,
                    ),
                    1,
                ):
                    current = row.id
                    elapsed = _number(row.elapsed_seconds)
                    rebuilt = sample_from_row(row, sensor_id=origin.sensor_id)
                    if (
                        row.sequence != sequence
                        or elapsed < previous
                        or elapsed > close_elapsed
                        or rebuilt.received_at > end
                        or row.is_synthetic != synthetic
                        or row.source_kind != origin.source_kind
                    ):
                        raise ValueError("inconsistent origin")
                    # Preflight representability of every logical instant and sleep duration.
                    start + timedelta(seconds=elapsed)
                    if not math.isfinite((elapsed - previous) / pacing):
                        raise ValueError("unrepresentable pacing")
                    inputs.append(_Input(row.id, elapsed, rebuilt))
                    previous = elapsed
            current = None
            clock = _ReplayClock(start)
            stage = "registry"
            with _REGISTRY_LOCK, self._factory() as db, db.begin():
                matches = repositories.find_sensors(
                    db,
                    kind="replay",
                    external_identifier=REPLAY_IDENTIFIER,
                )
                if len(matches) > 1:
                    raise ReplayError("ambiguous_identity")
                if matches:
                    sensor_id = matches[0].id
                else:
                    sensor_id = self._ids.new_id()
                    repositories.insert_sensor(
                        db,
                        id=sensor_id,
                        kind="replay",
                        external_identifier=REPLAY_IDENTIFIER,
                        created_at=clock.now_utc(),
                    )
            stage = "open"
            service = IngestionService(self._factory, clock, self._ids)
            opened = service._open_session(
                sensor_id=sensor_id,
                source_kind=SourceKind.REPLAY,
                is_synthetic=synthetic,
                config=config,
                origin_recording_session_id=origin_session_id,
            )
        except ReplayError:
            raise
        except Exception:
            raise ReplayError(stage, origin_sample_id=current) from None
        prepared = tuple(
            replace(
                item,
                sample=replace(item.sample, sensor_id=sensor_id, source_kind=SourceKind.REPLAY),
            )
            for item in inputs
        )
        return ReplayExecution(opened, service, clock, prepared, close_elapsed, pacing, self._sleep)
