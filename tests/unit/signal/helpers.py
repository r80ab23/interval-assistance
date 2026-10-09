"""Shared fixtures for signal tests. Values are test conventions, not physiological claims."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from interval_assistance.sensors.sample import HeartRateSample, SourceKind
from interval_assistance.signal import QualityState, ReasonCode, SignalQualityConfig

T0 = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
SENSOR_ID = uuid.UUID(int=1)

# The documented test vector (SCIENTIFIC_SPECIFICATION.md 5.1.1).
DOC_CONFIG_SOURCE: dict[str, Any] = {
    "config_id": "example-test-config",
    "config_version": "1",
    "hr_min_bpm": 10,
    "hr_max_bpm": 20,
    "max_jump_bpm": 5,
    "stale_after_seconds": 3.5,
    "gap_after_seconds": 7,
    "state_by_reason": {
        "duplicate_timestamp": "POOR",
        "out_of_order_timestamp": "POOR",
        "implausible_jump": "POOR",
        "gap": "MISSING",
        "stale": "STALE",
    },
    "no_findings_state": "GOOD",
}
DOC_CANONICAL_TEXT = (
    '{"config_id":"example-test-config","config_version":"1","format":"signal-quality-config/1",'
    '"gap_after_seconds":7,"hr_max_bpm":20,"hr_min_bpm":10,"max_jump_bpm":5,'
    '"no_findings_state":"GOOD","stale_after_seconds":3.5,"state_by_reason":'
    '{"duplicate_timestamp":"POOR","gap":"MISSING","implausible_jump":"POOR",'
    '"out_of_order_timestamp":"POOR","stale":"STALE"}}'
)
DOC_CONFIG_SHA256 = "b7f6ab26ad1f4cf4792f7378859d79b36ea7d705134e46d0a35f1dc2cb53eb08"


def make_config(**overrides: Any) -> SignalQualityConfig:
    data: dict[str, Any] = {**DOC_CONFIG_SOURCE, **overrides}
    return SignalQualityConfig.from_mapping(data)


def make_state_map(**overrides: QualityState) -> dict[ReasonCode, QualityState]:
    base = {
        ReasonCode.DUPLICATE_TIMESTAMP: QualityState.POOR,
        ReasonCode.OUT_OF_ORDER_TIMESTAMP: QualityState.POOR,
        ReasonCode.IMPLAUSIBLE_JUMP: QualityState.POOR,
        ReasonCode.GAP: QualityState.MISSING,
        ReasonCode.STALE: QualityState.STALE,
    }
    for name, state in overrides.items():
        base[ReasonCode(name)] = state
    return base


def sample(
    hr: float | None = 15.0,
    *,
    at: datetime | None = None,
    seconds: float = 0.0,
    device_timestamp: datetime | None = None,
    raw_payload: bytes | None = None,
) -> HeartRateSample:
    return HeartRateSample(
        sensor_id=SENSOR_ID,
        source_kind=SourceKind.SIMULATED,
        is_synthetic=True,
        received_hr=hr,
        received_at=at if at is not None else T0 + timedelta(seconds=seconds),
        device_timestamp=device_timestamp,
        raw_payload=raw_payload,
    )
