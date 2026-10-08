"""Manual heart-rate input: values entered by a person (coach/developer), flagged synthetic."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from interval_assistance.core.clock import Clock
from interval_assistance.core.errors import SensorConnectionError
from interval_assistance.sensors.base import ConnectionStatus, HeartRateSensor
from interval_assistance.sensors.sample import HeartRateSample, SourceKind


@dataclass(frozen=True, slots=True)
class _Stop:
    """End-of-run marker. It ends only the run that created it (see `_run`)."""

    run: int


class ManualHeartRateSensor(HeartRateSensor):
    """Each `start()` begins a new numbered run. `samples()` follows the run that is current
    when it is called and ends at that run's stop marker. Markers left over from earlier runs
    are skipped, and no queued sample is ever discarded."""

    source_kind = SourceKind.MANUAL

    def __init__(self, clock: Clock, sensor_id: uuid.UUID) -> None:
        self.sensor_id = sensor_id
        self._clock = clock
        self._status = ConnectionStatus.DISCONNECTED
        self._run = 0
        self._queue: asyncio.Queue[HeartRateSample | _Stop] = asyncio.Queue()

    @property
    def status(self) -> ConnectionStatus:
        return self._status

    async def connect(self) -> None:
        if self._status is ConnectionStatus.DISCONNECTED:
            self._status = ConnectionStatus.CONNECTED

    async def disconnect(self) -> None:
        await self.stop()
        self._status = ConnectionStatus.DISCONNECTED

    async def start(self) -> None:
        if self._status is ConnectionStatus.DISCONNECTED:
            raise SensorConnectionError("cannot start a disconnected sensor")
        if self._status is ConnectionStatus.CONNECTED:
            self._run += 1
            self._status = ConnectionStatus.STREAMING

    async def stop(self) -> None:
        if self._status is ConnectionStatus.STREAMING:
            self._status = ConnectionStatus.CONNECTED
            self._queue.put_nowait(_Stop(self._run))

    def submit(self, value: float) -> HeartRateSample:
        """Record a manually entered value, stamped with the injected clock. No validation."""
        if self._status is not ConnectionStatus.STREAMING:
            raise SensorConnectionError("manual sensor is not streaming")
        sample = HeartRateSample(
            sensor_id=self.sensor_id,
            source_kind=self.source_kind,
            is_synthetic=True,
            received_hr=value,
            received_at=self._clock.now_utc(),
        )
        self._queue.put_nowait(sample)
        return sample

    async def samples(self) -> AsyncIterator[HeartRateSample]:
        run = self._run
        while True:
            item = await self._queue.get()
            if isinstance(item, _Stop):
                if item.run == run:
                    return
                continue
            yield item
