"""Stateless per-sample validation (SCIENTIFIC_SPECIFICATION.md 5.1).

Validation only reports findings; it never alters a sample. Any finding makes a sample
INVALID (see quality.py). The in-memory sample carries the value exactly as received.
"""

from __future__ import annotations

import math
from datetime import datetime

from interval_assistance.sensors.sample import HeartRateSample
from interval_assistance.signal.config import SignalQualityConfig
from interval_assistance.signal.reasons import ReasonCode


def is_timezone_aware(moment: datetime) -> bool:
    return moment.tzinfo is not None and moment.tzinfo.utcoffset(moment) is not None


def validate_sample(sample: HeartRateSample, config: SignalQualityConfig) -> tuple[ReasonCode, ...]:
    """Validation findings for one sample, in a fixed order (value, then timestamp)."""
    findings: list[ReasonCode] = []
    value = sample.received_hr
    if value is None:
        # No value. With a payload the delivery carried something unusable; without one,
        # nothing at all was delivered.
        findings.append(
            ReasonCode.MISSING if sample.raw_payload is None else ReasonCode.MALFORMED_SAMPLE
        )
    elif not math.isfinite(value):
        findings.append(ReasonCode.MALFORMED_SAMPLE)
    elif not config.hr_min_bpm <= value <= config.hr_max_bpm:
        findings.append(ReasonCode.IMPOSSIBLE_HR)

    device_timestamp = sample.device_timestamp
    if device_timestamp is not None and not is_timezone_aware(device_timestamp):
        findings.append(ReasonCode.INVALID_TIMESTAMP)
    return tuple(findings)
