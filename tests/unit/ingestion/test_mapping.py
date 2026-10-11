from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest

from interval_assistance.ingestion.mapping import (
    nonfinite_marker,
    raw_row_values,
    sample_from_row,
    stored_device_timestamp,
    stored_value,
)
from interval_assistance.sensors.sample import HeartRateSample
from interval_assistance.signal import ReasonCode, TimestampAxis, validate_sample
from interval_assistance.signal.quality import timestamp_with_axis
from tests.unit.signal.helpers import SENSOR_ID, T0, make_config, sample

SAMPLE_ID = uuid.UUID(int=10)
SESSION_ID = uuid.UUID(int=11)
PLUS_5_30 = timezone(timedelta(hours=5, minutes=30))


def values(s: HeartRateSample, **changes: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "sample_id": SAMPLE_ID,
        "session_id": SESSION_ID,
        "sequence": 1,
        "ingestion_timestamp": T0,
        "elapsed_seconds": 0.0,
    }
    return raw_row_values(s, **(base | changes))


@dataclass
class Row:
    received_hr: float | None
    received_hr_nonfinite: str | None
    raw_payload: bytes | None
    device_timestamp: datetime | None
    received_at: datetime
    source_kind: str
    is_synthetic: bool
    adapter_quality_hint: str | None


def row_from(v: dict[str, Any]) -> Row:
    return Row(
        received_hr=v["received_hr"],
        received_hr_nonfinite=v["received_hr_nonfinite"],
        raw_payload=v["raw_payload"],
        device_timestamp=v["device_timestamp"],
        received_at=v["received_at"],
        source_kind=v["source_kind"],
        is_synthetic=v["is_synthetic"],
        adapter_quality_hint=v["adapter_quality_hint"],
    )


def test_finite_value_is_stored_as_a_float_without_marker() -> None:
    row = values(sample(61))
    assert row["received_hr"] == 61.0 and isinstance(row["received_hr"], float)
    assert row["received_hr_nonfinite"] is None
    assert row["sequence"] == 1 and row["id"] == SAMPLE_ID
    assert row["recording_session_id"] == SESSION_ID and row["origin_sample_id"] is None


@pytest.mark.parametrize("payload", [None, b"\x00\x7f"])
def test_no_value_is_stored_as_null_with_the_payload_kept_verbatim(payload: bytes | None) -> None:
    row = values(sample(None, raw_payload=payload))
    assert row["received_hr"] is None and row["received_hr_nonfinite"] is None
    assert row["raw_payload"] == payload


@pytest.mark.parametrize(
    ("value", "marker"),
    [(math.nan, "nan"), (math.inf, "+inf"), (-math.inf, "-inf")],
)
def test_non_finite_values_become_a_marker_with_a_null_value(value: float, marker: str) -> None:
    row = values(sample(value, raw_payload=b"p"))
    assert row["received_hr"] is None
    assert row["received_hr_nonfinite"] == marker
    assert row["raw_payload"] == b"p"
    assert nonfinite_marker(value) == marker and stored_value(value) is None


def test_finite_and_missing_values_have_no_marker() -> None:
    assert nonfinite_marker(60.0) is None and nonfinite_marker(None) is None
    assert nonfinite_marker(10**400) is None  # finite, so never a marker


@pytest.mark.parametrize("value", [10**400, -(10**400)])
def test_a_huge_int_is_validated_but_cannot_be_stored_and_leaks_no_overflow(value: int) -> None:
    huge = sample(value)
    assert validate_sample(huge, make_config()) == (ReasonCode.IMPOSSIBLE_HR,)
    with pytest.raises(ValueError, match="outside the range of a float"):
        values(huge)


def test_aware_non_utc_timestamps_keep_their_instant_in_utc() -> None:
    received = datetime(2026, 1, 1, 17, 30, tzinfo=PLUS_5_30)  # 12:00 UTC
    device = datetime(2026, 1, 1, 17, 31, tzinfo=PLUS_5_30)
    row = values(sample(60, at=received, device_timestamp=device))
    assert row["received_at"] == received == T0
    assert row["device_timestamp"] == device == T0 + timedelta(minutes=1)
    for key in ("received_at", "device_timestamp"):
        assert row[key].utcoffset() == timedelta(0)


def test_ingestion_timestamp_is_normalized_to_utc_too() -> None:
    local = datetime(2026, 1, 1, 17, 30, tzinfo=PLUS_5_30)
    stored = values(sample(60), ingestion_timestamp=local)["ingestion_timestamp"]
    assert stored == T0 and stored.utcoffset() == timedelta(0)


def test_naive_device_timestamp_is_stored_as_null() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert values(sample(60, device_timestamp=naive))["device_timestamp"] is None
    assert stored_device_timestamp(naive) is None and stored_device_timestamp(None) is None


def test_source_synthetic_and_hint_metadata_are_preserved() -> None:
    s = HeartRateSample(
        sensor_id=SENSOR_ID,
        source_kind=sample().source_kind,
        is_synthetic=True,
        received_hr=60.0,
        received_at=T0,
        quality_hint="hint",
    )
    row = values(s)
    assert row["source_kind"] == "simulated" and row["is_synthetic"] is True
    assert row["adapter_quality_hint"] == "hint"


@pytest.mark.parametrize("value", [60.0, None, math.nan, math.inf, -math.inf])
def test_reverse_mapping_reconstructs_the_sample(value: float | None) -> None:
    original = sample(value, raw_payload=b"x", device_timestamp=T0 + timedelta(seconds=1))
    rebuilt = sample_from_row(row_from(values(original)), sensor_id=SENSOR_ID)
    assert rebuilt.sensor_id == SENSOR_ID and rebuilt.raw_payload == b"x"
    assert rebuilt.received_at == original.received_at
    assert rebuilt.device_timestamp == original.device_timestamp
    if value is None:
        assert rebuilt.received_hr is None
    elif math.isnan(value):
        assert rebuilt.received_hr is not None and math.isnan(rebuilt.received_hr)
    else:
        assert rebuilt.received_hr == value


def test_reverse_mapping_derives_the_timestamp_axis_from_the_device_timestamp() -> None:
    with_device = sample(60, device_timestamp=T0 + timedelta(seconds=2))
    without = sample(60)
    naive = sample(60, device_timestamp=datetime(2026, 1, 1, 12, 0, 0))
    axes = [
        timestamp_with_axis(sample_from_row(row_from(values(s)), sensor_id=SENSOR_ID))[1]
        for s in (with_device, without, naive)
    ]
    assert axes == [TimestampAxis.DEVICE, TimestampAxis.RECEIVE, TimestampAxis.RECEIVE]


def test_reverse_mapping_attaches_utc_to_zone_less_database_values() -> None:
    """SQLite returns the stored UTC wall clock without a zone."""
    row = row_from(values(sample(60, device_timestamp=T0)))
    row.received_at = row.received_at.replace(tzinfo=None)
    assert row.device_timestamp is not None
    row.device_timestamp = row.device_timestamp.replace(tzinfo=None)
    rebuilt = sample_from_row(row, sensor_id=SENSOR_ID)
    assert rebuilt.received_at == T0 and rebuilt.received_at.tzinfo == UTC
    assert rebuilt.device_timestamp == T0
