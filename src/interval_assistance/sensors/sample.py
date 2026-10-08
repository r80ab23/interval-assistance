"""Normalized in-memory heart-rate sample.

This is a domain contract, not a persistence model: Phase 1 has no sample table. The type
performs no plausibility checks; validation and signal quality are Phase 2.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class SourceKind(StrEnum):
    REAL = "real"
    SIMULATED = "simulated"
    REPLAY = "replay"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class HeartRateSample:
    """One heart-rate reading exactly as the adapter observed it.

    received_hr: value as received, in beats per minute, unmodified.
    device_timestamp: sensor-supplied time, if any (may be absent or unreliable).
    received_at: adapter-observed receive time (timezone-aware UTC).
    is_synthetic: True for any data not recorded from a real sensor on a real person.
    quality_hint: optional adapter-supplied hint; never computed in Phase 1.
    """

    sensor_id: uuid.UUID
    source_kind: SourceKind
    is_synthetic: bool
    received_hr: float
    received_at: datetime
    device_timestamp: datetime | None = None
    quality_hint: str | None = None

    def __post_init__(self) -> None:
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        if self.source_kind is not SourceKind.REAL and not self.is_synthetic:
            raise ValueError("non-real sources must be flagged synthetic")
