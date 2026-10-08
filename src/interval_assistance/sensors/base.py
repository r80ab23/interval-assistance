"""Generic heart-rate sensor interface. Interval rules never live in adapters."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Callable
from enum import StrEnum

from interval_assistance.core.errors import SensorConnectionError
from interval_assistance.sensors.sample import HeartRateSample, SourceKind


class ConnectionStatus(StrEnum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    STREAMING = "streaming"


class HeartRateSensor(ABC):
    """connect, disconnect, start, stop, receive samples, connection status."""

    sensor_id: uuid.UUID
    source_kind: SourceKind

    @property
    @abstractmethod
    def status(self) -> ConnectionStatus: ...

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    def samples(self) -> AsyncIterator[HeartRateSample]:
        """Async stream of samples; ends when the sensor is stopped."""


SensorFactory = Callable[[], HeartRateSensor]


class SensorProvider:
    """Registry selecting sensor implementations by name. Phase 1 registers none by default."""

    def __init__(self) -> None:
        self._factories: dict[str, SensorFactory] = {}

    def register(self, name: str, factory: SensorFactory) -> None:
        if name in self._factories:
            raise ValueError(f"sensor kind already registered: {name}")
        self._factories[name] = factory

    def names(self) -> list[str]:
        return sorted(self._factories)

    def create(self, name: str) -> HeartRateSensor:
        try:
            factory = self._factories[name]
        except KeyError:
            raise SensorConnectionError(
                f"unknown sensor kind: {name}", details={"kind": name}
            ) from None
        return factory()
