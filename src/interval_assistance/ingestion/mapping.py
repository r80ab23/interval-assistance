"""Mapping between the in-memory sample and its stored raw row (DATA_MODEL.md 4.6).

Pure functions: no clock, database or I/O. Timestamps are stored as UTC instants, a non-finite
value is stored as a class marker with a NULL value, and nothing is repaired or reinterpreted.
"""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

from interval_assistance.sensors.sample import HeartRateSample, SourceKind
from interval_assistance.signal.validation import is_finite_number


class StoredRawRow(Protocol):
    """The columns of a stored raw row that `sample_from_row` reads (satisfied by the model)."""

    @property
    def received_hr(self) -> float | None: ...
    @property
    def received_hr_nonfinite(self) -> str | None: ...
    @property
    def raw_payload(self) -> bytes | None: ...
    @property
    def device_timestamp(self) -> datetime | None: ...
    @property
    def received_at(self) -> datetime: ...
    @property
    def source_kind(self) -> str: ...
    @property
    def is_synthetic(self) -> bool: ...
    @property
    def adapter_quality_hint(self) -> str | None: ...


_NONFINITE_VALUES = {"nan": math.nan, "+inf": math.inf, "-inf": -math.inf}


def nonfinite_marker(value: float | None) -> str | None:
    """The stored class of a non-finite value (`nan`, `+inf`, `-inf`), else None."""
    if value is None or is_finite_number(value):
        return None
    if math.isnan(value):
        return "nan"
    return "+inf" if value > 0 else "-inf"


def stored_value(value: float | None) -> float | None:
    """The finite value to store, or None (no value, or a non-finite value kept as a marker).

    An int beyond the float range has no representation in the `received_hr` float column and
    is rejected here, before anything is written, rather than being altered or dropped."""
    if value is None or not is_finite_number(value):
        return None
    try:
        return float(value)
    except OverflowError:
        raise ValueError("received_hr is a finite number outside the range of a float") from None


def to_utc(moment: datetime) -> datetime:
    """An aware instant expressed in UTC (the instant is preserved)."""
    return moment.astimezone(UTC)


def stored_device_timestamp(moment: datetime | None) -> datetime | None:
    """UTC instant, or None for no timestamp and for a naive one (it represents no instant)."""
    if moment is None or moment.tzinfo is None or moment.tzinfo.utcoffset(moment) is None:
        return None
    return to_utc(moment)


def raw_row_values(
    sample: HeartRateSample,
    *,
    sample_id: uuid.UUID,
    session_id: uuid.UUID,
    sequence: int,
    ingestion_timestamp: datetime,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Column values for the raw row of `sample`. `origin_sample_id` is left to replay."""
    return {
        "id": sample_id,
        "recording_session_id": session_id,
        "sequence": sequence,
        "received_hr": stored_value(sample.received_hr),
        "received_hr_nonfinite": nonfinite_marker(sample.received_hr),
        "raw_payload": sample.raw_payload,
        "device_timestamp": stored_device_timestamp(sample.device_timestamp),
        "received_at": to_utc(sample.received_at),
        "ingestion_timestamp": to_utc(ingestion_timestamp),
        "elapsed_seconds": elapsed_seconds,
        "source_kind": sample.source_kind.value,
        "is_synthetic": sample.is_synthetic,
        "adapter_quality_hint": sample.quality_hint,
        "origin_sample_id": None,
    }


def _aware_utc(moment: datetime) -> datetime:
    # SQLite returns the stored UTC wall clock without a zone; other backends return aware values.
    return moment.replace(tzinfo=UTC) if moment.tzinfo is None else moment.astimezone(UTC)


def sample_from_row(row: StoredRawRow, *, sensor_id: uuid.UUID) -> HeartRateSample:
    """The in-memory sample stored in `row`. A stored device timestamp puts the sample on the
    device timestamp axis, NULL on the receive axis. The sensor comes from the row's session."""
    if row.received_hr_nonfinite is not None:
        received_hr: float | None = _NONFINITE_VALUES[row.received_hr_nonfinite]
    else:
        received_hr = row.received_hr
    return HeartRateSample(
        sensor_id=sensor_id,
        source_kind=SourceKind(row.source_kind),
        is_synthetic=row.is_synthetic,
        received_hr=received_hr,
        received_at=_aware_utc(row.received_at),
        device_timestamp=(
            None if row.device_timestamp is None else _aware_utc(row.device_timestamp)
        ),
        quality_hint=row.adapter_quality_hint,
        raw_payload=row.raw_payload,
    )
