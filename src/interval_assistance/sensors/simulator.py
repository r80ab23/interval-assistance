"""Deterministic synthetic heart-rate generator.

This is a declared synthetic generator, not a physiological model: a seeded bounded random
walk. The caller must supply the bounds; no values are assumed. Every sample is flagged
synthetic. Given the same config, seed and clock start, the stream is identical.
"""

from __future__ import annotations

import asyncio
import random
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import IntEnum

from interval_assistance.core.clock import Clock
from interval_assistance.core.errors import SensorConnectionError
from interval_assistance.sensors.base import ConnectionStatus, HeartRateSensor
from interval_assistance.sensors.sample import HeartRateSample, SourceKind


class SimulationSpeed(IntEnum):
    X1 = 1
    X5 = 5
    X20 = 20


@dataclass(frozen=True, slots=True)
class SimulatorConfig:
    seed: int
    start_value: float
    min_value: float
    max_value: float
    max_step: float
    interval_seconds: float = 1.0
    speed: SimulationSpeed = SimulationSpeed.X1

    def __post_init__(self) -> None:
        if not self.min_value <= self.start_value <= self.max_value:
            raise ValueError("start_value must lie within [min_value, max_value]")
        if self.max_step < 0:
            raise ValueError("max_step must be non-negative")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")


def generate_values(config: SimulatorConfig) -> Iterator[float]:
    """Pure, infinite, reproducible value stream (depends only on the config)."""
    rng = random.Random(config.seed)
    value = config.start_value
    while True:
        yield value
        value += rng.uniform(-config.max_step, config.max_step)
        value = min(config.max_value, max(config.min_value, value))


Sleep = Callable[[float], Awaitable[None]]


class SimulatorHeartRateSensor(HeartRateSensor):
    """Simulated sensor. Sample times are nominal (start + n * interval), so they do not
    depend on wall-clock jitter; `speed` only scales real-time pacing between samples."""

    source_kind = SourceKind.SIMULATED

    def __init__(
        self,
        config: SimulatorConfig,
        clock: Clock,
        sensor_id: uuid.UUID,
        *,
        sleep: Sleep = asyncio.sleep,
        max_samples: int | None = None,
    ) -> None:
        self.sensor_id = sensor_id
        self._config = config
        self._clock = clock
        self._sleep = sleep
        self._max_samples = max_samples
        self._status = ConnectionStatus.DISCONNECTED
        self._start_time: datetime | None = None

    @property
    def status(self) -> ConnectionStatus:
        return self._status

    async def connect(self) -> None:
        if self._status is ConnectionStatus.DISCONNECTED:
            self._status = ConnectionStatus.CONNECTED

    async def disconnect(self) -> None:
        self._status = ConnectionStatus.DISCONNECTED
        self._start_time = None

    async def start(self) -> None:
        if self._status is ConnectionStatus.DISCONNECTED:
            raise SensorConnectionError("cannot start a disconnected sensor")
        self._start_time = self._clock.now_utc()
        self._status = ConnectionStatus.STREAMING

    async def stop(self) -> None:
        if self._status is ConnectionStatus.STREAMING:
            self._status = ConnectionStatus.CONNECTED

    async def samples(self) -> AsyncIterator[HeartRateSample]:
        if self._status is not ConnectionStatus.STREAMING or self._start_time is None:
            raise SensorConnectionError("sensor is not streaming")
        start = self._start_time
        step = timedelta(seconds=self._config.interval_seconds)
        pause = self._config.interval_seconds / int(self._config.speed)
        for index, value in enumerate(generate_values(self._config)):
            if self._status is not ConnectionStatus.STREAMING:
                return
            if self._max_samples is not None and index >= self._max_samples:
                return
            yield HeartRateSample(
                sensor_id=self.sensor_id,
                source_kind=self.source_kind,
                is_synthetic=True,
                received_hr=value,
                received_at=start + index * step,
            )
            await self._sleep(pause)
