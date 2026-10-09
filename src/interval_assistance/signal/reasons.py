"""Reason codes and quality states (SCIENTIFIC_SPECIFICATION.md 5 and 5.1)."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum


class ReasonCode(StrEnum):
    # Validation (stateless, per sample). Any of these makes a sample INVALID.
    MALFORMED_SAMPLE = "malformed_sample"
    MISSING = "missing"
    IMPOSSIBLE_HR = "impossible_hr"
    INVALID_TIMESTAMP = "invalid_timestamp"
    # Signal quality (stateful).
    DUPLICATE_TIMESTAMP = "duplicate_timestamp"
    OUT_OF_ORDER_TIMESTAMP = "out_of_order_timestamp"
    IMPLAUSIBLE_JUMP = "implausible_jump"
    GAP = "gap"
    STALE = "stale"


class QualityState(StrEnum):
    UNKNOWN = "UNKNOWN"
    GOOD = "GOOD"
    ACCEPTABLE = "ACCEPTABLE"
    POOR = "POOR"
    INVALID = "INVALID"
    STALE = "STALE"
    MISSING = "MISSING"


VALIDATION_REASONS = frozenset(
    {
        ReasonCode.MALFORMED_SAMPLE,
        ReasonCode.MISSING,
        ReasonCode.IMPOSSIBLE_HR,
        ReasonCode.INVALID_TIMESTAMP,
    }
)

SIGNAL_QUALITY_REASONS = frozenset(
    {
        ReasonCode.DUPLICATE_TIMESTAMP,
        ReasonCode.OUT_OF_ORDER_TIMESTAMP,
        ReasonCode.IMPLAUSIBLE_JUMP,
        ReasonCode.GAP,
        ReasonCode.STALE,
    }
)

# Fixed aggregation order, highest precedence first. A project convention for combining
# findings, not a physiological ordering (SCIENTIFIC_SPECIFICATION.md 5.1).
STATE_PRECEDENCE: tuple[QualityState, ...] = (
    QualityState.INVALID,
    QualityState.MISSING,
    QualityState.STALE,
    QualityState.POOR,
    QualityState.ACCEPTABLE,
    QualityState.GOOD,
    QualityState.UNKNOWN,
)

_RANK = {state: rank for rank, state in enumerate(STATE_PRECEDENCE)}


def worst_state(states: Iterable[QualityState]) -> QualityState:
    """The highest-precedence state among `states`. Raises ValueError when empty: the caller
    must apply the configured `no_findings_state` itself."""
    collected = list(states)
    if not collected:
        raise ValueError("worst_state needs at least one state")
    return min(collected, key=_RANK.__getitem__)
