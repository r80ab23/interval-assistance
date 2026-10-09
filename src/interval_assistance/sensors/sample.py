"""Normalized in-memory heart-rate sample.

This is a domain contract, not a persistence model. The type performs no plausibility checks
on the value or on `device_timestamp`; validation and signal quality live in the `signal`
package (ARCHITECTURE.md 5.1a).
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


# Sources whose data is, by construction, not recorded from a real sensor on a real person.
# A replay sample is not in this set: it inherits `is_synthetic` from the sample it replays.
_ALWAYS_SYNTHETIC = frozenset({SourceKind.SIMULATED, SourceKind.MANUAL})


@dataclass(frozen=True, slots=True)
class HeartRateSample:
    """One heart-rate reading exactly as the adapter observed it.

    received_hr: value as received, in beats per minute, unmodified. None when no value could
        be taken from the delivery (malformed or empty input); NaN and infinities are carried
        as received.
    device_timestamp: sensor-supplied time, if any (may be absent, unreliable or naive).
    received_at: adapter-observed receive time (timezone-aware).
    is_synthetic: True for any data not recorded from a real sensor on a real person.
    quality_hint: optional adapter-supplied hint; never computed or interpreted here.
    raw_payload: the bytes the adapter actually supplied, where it has them. Never fabricated.
    """

    sensor_id: uuid.UUID
    source_kind: SourceKind
    is_synthetic: bool
    received_hr: float | None
    received_at: datetime
    device_timestamp: datetime | None = None
    quality_hint: str | None = None
    raw_payload: bytes | None = None

    def __post_init__(self) -> None:
        if self.received_at.tzinfo is None:
            raise ValueError("received_at must be timezone-aware")
        if self.source_kind in _ALWAYS_SYNTHETIC and not self.is_synthetic:
            raise ValueError("simulated and manual sources must be flagged synthetic")
