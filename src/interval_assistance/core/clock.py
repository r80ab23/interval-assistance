"""Authoritative time source. Domain and application code never read system time directly."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta


class Clock(ABC):
    """Injected time source providing wall-clock UTC time and monotonic elapsed time."""

    @abstractmethod
    def now_utc(self) -> datetime:
        """Timezone-aware wall-clock time in UTC."""

    @abstractmethod
    def monotonic(self) -> float:
        """Monotonic seconds; only differences are meaningful."""


class SystemClock(Clock):
    def now_utc(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


class ManualClock(Clock):
    """Deterministic clock advanced explicitly; used by tests and deterministic simulation."""

    def __init__(self, start: datetime, monotonic_start: float = 0.0) -> None:
        if start.tzinfo is None or start.utcoffset() != timedelta(0):
            raise ValueError("ManualClock start must be timezone-aware UTC")
        self._now = start
        self._monotonic = monotonic_start

    def now_utc(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._monotonic

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("a clock cannot move backwards")
        self._now = self._now + timedelta(seconds=seconds)
        self._monotonic += seconds
