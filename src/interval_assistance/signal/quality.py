"""Stateful signal-quality assessment (SCIENTIFIC_SPECIFICATION.md 5.1).

Pure and deterministic: no clock, database or I/O. The caller owns the stream state and passes
an explicit `now` for staleness. Findings are flags; nothing is filtered, repaired or
interpolated.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from interval_assistance.sensors.sample import HeartRateSample
from interval_assistance.signal.config import SignalQualityConfig
from interval_assistance.signal.reasons import QualityState, ReasonCode, worst_state
from interval_assistance.signal.validation import is_timezone_aware, validate_sample


class TimestampAxis(StrEnum):
    """Which clock an effective timestamp was read from. Timestamps on different axes are not
    comparable, so duplicate/out-of-order checks only run between samples on the same axis."""

    DEVICE = "device"
    RECEIVE = "receive"


@dataclass(frozen=True, slots=True, kw_only=True)
class StreamState:
    """What the next assessment needs from the samples before it (all UTC instants).

    last_timestamp, last_timestamp_axis: the previous sample's effective timestamp and the axis
        it was read from. Both set or both None; an axis-less timestamp is rejected, never
        compared.
    last_received_at: the previous sample's (last-arrived) receive time; the `gap` reference.
    max_received_at: the largest receive time observed so far; the `stale` reference. It never
        moves backwards. Set exactly when last_received_at is, and never below it.
    last_valid_hr: the value of the most recent sample that passed validation.
    A new stream starts with every field None. Every field is keyword-only and an inconsistent
    combination raises ValueError, so there is no legacy or partial state."""

    last_timestamp: datetime | None = None
    last_timestamp_axis: TimestampAxis | None = None
    last_received_at: datetime | None = None
    max_received_at: datetime | None = None
    last_valid_hr: float | None = None

    def __post_init__(self) -> None:
        if (self.last_timestamp is None) != (self.last_timestamp_axis is None):
            raise ValueError("last_timestamp and last_timestamp_axis must be set together")
        if (self.last_received_at is None) != (self.max_received_at is None):
            raise ValueError("last_received_at and max_received_at must be set together")
        for moment in (self.last_timestamp, self.last_received_at, self.max_received_at):
            if moment is not None and not is_timezone_aware(moment):
                raise ValueError("stream-state instants must be timezone-aware")
        if self.last_timestamp_axis is not None and not isinstance(
            self.last_timestamp_axis, TimestampAxis
        ):
            raise ValueError("last_timestamp_axis must be a TimestampAxis")
        if (
            self.last_received_at is not None
            and self.max_received_at is not None
            and self.max_received_at < self.last_received_at
        ):
            raise ValueError("max_received_at must not be below last_received_at")


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


def timestamp_with_axis(sample: HeartRateSample) -> tuple[datetime, TimestampAxis]:
    """`device_timestamp` when present and valid (timezone-aware), otherwise `received_at`
    (including a naive device timestamp), normalized to UTC with the instant preserved, plus
    the axis it was read from."""
    device = sample.device_timestamp
    if device is not None and is_timezone_aware(device):
        return _utc(device), TimestampAxis.DEVICE
    return _utc(sample.received_at), TimestampAxis.RECEIVE


def effective_timestamp(sample: HeartRateSample) -> datetime:
    """The effective timestamp alone (see `timestamp_with_axis`)."""
    return timestamp_with_axis(sample)[0]


def assess_sample(
    sample: HeartRateSample, state: StreamState, config: SignalQualityConfig
) -> AssessmentStep:
    """Assess one sample against the stream so far.

    Per-sample reasons: the validation findings, then `duplicate_timestamp` or
    `out_of_order_timestamp` (same timestamp axis only), then `implausible_jump` (value-based).
    Every sample, valid or not, counts as a receive event for `gap` and `stale`. A `gap` is
    not a per-sample reason; it is returned as a closed range between the previous and this
    sample's receive times."""
    validation = validate_sample(sample, config)
    reasons = list(validation)

    timestamp, axis = timestamp_with_axis(sample)
    if state.last_timestamp is not None and state.last_timestamp_axis is axis:
        # Same axis only: a device timestamp is never compared with a receive timestamp, so a
        # mixed pair yields neither finding. The previous sample is always the reference.
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
        last_timestamp_axis=axis,
        # Gap reference: the last-arrived sample, valid or not.
        last_received_at=received_at,
        # Stale reference: the maximum receive time, never moved backwards.
        max_received_at=(
            received_at
            if state.max_received_at is None
            else max(state.max_received_at, received_at)
        ),
        last_valid_hr=state.last_valid_hr if validation else value,
    )
    return AssessmentStep(SampleAssessment(quality, tuple(reasons)), gap, next_state)


def evaluate_stale(
    last_received_at: datetime, now: datetime, config: SignalQualityConfig
) -> RangeFinding | None:
    """The open `stale` range if the age of the latest receive time (pass the stream state's
    `max_received_at`, the maximum observed, never the last-arrived one) exceeds
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
