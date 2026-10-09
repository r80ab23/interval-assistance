"""Stateful signal-quality assessment (SCIENTIFIC_SPECIFICATION.md 5.1).

Pure and deterministic: no clock, database or I/O. The caller owns the stream state and passes
an explicit `now` for staleness. Findings are flags; nothing is filtered, repaired or
interpolated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from interval_assistance.sensors.sample import HeartRateSample
from interval_assistance.signal.config import SignalQualityConfig
from interval_assistance.signal.reasons import QualityState, ReasonCode, worst_state
from interval_assistance.signal.validation import is_timezone_aware, validate_sample


@dataclass(frozen=True, slots=True)
class StreamState:
    """What the next assessment needs from the samples before it (all UTC instants).

    last_timestamp: the previous sample's effective timestamp.
    last_received_at: the previous sample's receive time.
    last_valid_hr: the value of the most recent sample that passed validation.
    A new stream starts with all three None (no previous sample)."""

    last_timestamp: datetime | None = None
    last_received_at: datetime | None = None
    last_valid_hr: float | None = None


@dataclass(frozen=True, slots=True)
class SampleAssessment:
    state: QualityState
    reasons: tuple[ReasonCode, ...]


@dataclass(frozen=True, slots=True)
class RangeFinding:
    """A `gap` (closed) or `stale` (open, up to the evaluation time) range, in UTC."""

    reason: ReasonCode
    state: QualityState
    start: datetime
    end: datetime


@dataclass(frozen=True, slots=True)
class AssessmentStep:
    assessment: SampleAssessment
    gap: RangeFinding | None
    next_state: StreamState


def _utc(moment: datetime) -> datetime:
    return moment.astimezone(UTC)


def effective_timestamp(sample: HeartRateSample) -> datetime:
    """`device_timestamp` when present and valid (timezone-aware), otherwise `received_at`,
    normalized to UTC with the represented instant preserved."""
    device = sample.device_timestamp
    if device is not None and is_timezone_aware(device):
        return _utc(device)
    return _utc(sample.received_at)


def assess_sample(
    sample: HeartRateSample, state: StreamState, config: SignalQualityConfig
) -> AssessmentStep:
    """Assess one sample against the stream so far.

    Per-sample reasons: the validation findings, then `duplicate_timestamp` or
    `out_of_order_timestamp`, then `implausible_jump`. A `gap` is not a per-sample reason; it
    is returned as a closed range between the previous and this sample's receive times."""
    validation = validate_sample(sample, config)
    reasons = list(validation)

    timestamp = effective_timestamp(sample)
    if state.last_timestamp is not None:
        # Literal reading of the specification: this sample's effective timestamp is
        # compared with the previous sample's effective timestamp.
        if timestamp == state.last_timestamp:
            reasons.append(ReasonCode.DUPLICATE_TIMESTAMP)
        elif timestamp < state.last_timestamp:
            reasons.append(ReasonCode.OUT_OF_ORDER_TIMESTAMP)

    value = sample.received_hr
    if (
        value is not None
        and math.isfinite(value)
        and state.last_valid_hr is not None
        and abs(value - state.last_valid_hr) > config.max_jump_bpm
    ):
        reasons.append(ReasonCode.IMPLAUSIBLE_JUMP)

    states = [QualityState.INVALID] if validation else []
    states.extend(config.state_by_reason[reason] for reason in reasons if reason not in validation)
    quality = worst_state(states) if states else config.no_findings_state

    received_at = _utc(sample.received_at)
    gap: RangeFinding | None = None
    if state.last_received_at is not None:
        elapsed = (received_at - state.last_received_at).total_seconds()
        if elapsed > config.gap_after_seconds:
            gap = RangeFinding(
                reason=ReasonCode.GAP,
                state=config.state_by_reason[ReasonCode.GAP],
                start=state.last_received_at,
                end=received_at,
            )

    next_state = StreamState(
        last_timestamp=timestamp,
        last_received_at=received_at,
        last_valid_hr=state.last_valid_hr if validation else value,
    )
    return AssessmentStep(SampleAssessment(quality, tuple(reasons)), gap, next_state)


def evaluate_stale(
    last_received_at: datetime, now: datetime, config: SignalQualityConfig
) -> RangeFinding | None:
    """The open `stale` range if the age of the latest receive time exceeds
    `stale_after_seconds` at the explicitly supplied `now`, otherwise None. Pure: nothing is
    persisted here."""
    if not (is_timezone_aware(last_received_at) and is_timezone_aware(now)):
        raise ValueError("last_received_at and now must be timezone-aware")
    start, end = _utc(last_received_at), _utc(now)
    if (end - start).total_seconds() > config.stale_after_seconds:
        return RangeFinding(
            reason=ReasonCode.STALE,
            state=config.state_by_reason[ReasonCode.STALE],
            start=start,
            end=end,
        )
    return None
