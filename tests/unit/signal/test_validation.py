from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta, timezone

import pytest

from interval_assistance.signal import ReasonCode, validate_sample

from .helpers import T0, make_config, sample

CONFIG = make_config()  # hr bounds are the documented test convention [10, 20]


def test_a_clean_sample_has_no_findings() -> None:
    assert validate_sample(sample(15.0), CONFIG) == ()


@pytest.mark.parametrize("value", [10.0, 20.0, 10.0000001, 19.9999999])
def test_bounds_are_inclusive(value: float) -> None:
    assert validate_sample(sample(value), CONFIG) == ()


@pytest.mark.parametrize("value", [9.9999999, 20.0000001, 0.0, -1.0, 1e9])
def test_finite_values_outside_the_bounds_are_impossible_hr(value: float) -> None:
    assert validate_sample(sample(value), CONFIG) == (ReasonCode.IMPOSSIBLE_HR,)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("payload", [None, b"raw"])
def test_non_finite_values_are_malformed_never_out_of_range(
    value: float, payload: bytes | None
) -> None:
    assert validate_sample(sample(value, raw_payload=payload), CONFIG) == (
        ReasonCode.MALFORMED_SAMPLE,
    )


def test_no_value_but_a_payload_is_malformed() -> None:
    assert validate_sample(sample(None, raw_payload=b"\xff\x00"), CONFIG) == (
        ReasonCode.MALFORMED_SAMPLE,
    )


def test_neither_value_nor_payload_is_missing() -> None:
    assert validate_sample(sample(None), CONFIG) == (ReasonCode.MISSING,)


def test_empty_payload_still_counts_as_a_delivered_payload() -> None:
    assert validate_sample(sample(None, raw_payload=b""), CONFIG) == (ReasonCode.MALFORMED_SAMPLE,)


def test_naive_device_timestamp_is_invalid_timestamp() -> None:
    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert validate_sample(sample(15.0, device_timestamp=naive), CONFIG) == (
        ReasonCode.INVALID_TIMESTAMP,
    )


@pytest.mark.parametrize("offset_hours", [0, 3, -5, 14, -12])
def test_aware_device_timestamps_in_any_offset_are_valid(offset_hours: int) -> None:
    moment = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone(timedelta(hours=offset_hours)))
    assert validate_sample(sample(15.0, device_timestamp=moment), CONFIG) == ()


def test_absent_device_timestamp_is_not_a_finding() -> None:
    assert validate_sample(sample(15.0, device_timestamp=None), CONFIG) == ()


def test_value_and_timestamp_findings_combine_in_a_fixed_order() -> None:
    naive = datetime(2026, 1, 1)
    assert validate_sample(sample(99.0, device_timestamp=naive), CONFIG) == (
        ReasonCode.IMPOSSIBLE_HR,
        ReasonCode.INVALID_TIMESTAMP,
    )
    assert validate_sample(sample(None, device_timestamp=naive), CONFIG) == (
        ReasonCode.MISSING,
        ReasonCode.INVALID_TIMESTAMP,
    )


def test_validation_does_not_modify_the_sample() -> None:
    original = sample(99.0, device_timestamp=datetime(2026, 1, 1), raw_payload=b"x")
    snapshot = (original.received_hr, original.device_timestamp, original.raw_payload)
    validate_sample(original, CONFIG)
    assert snapshot == (original.received_hr, original.device_timestamp, original.raw_payload)


def test_received_at_is_not_validated_here() -> None:
    far_future = datetime(2999, 1, 1, tzinfo=UTC)
    assert validate_sample(sample(15.0, at=far_future), CONFIG) == ()
    assert far_future > T0
