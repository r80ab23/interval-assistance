from __future__ import annotations

import itertools

import pytest

from interval_assistance.signal import (
    SIGNAL_QUALITY_REASONS,
    STATE_PRECEDENCE,
    VALIDATION_REASONS,
    QualityState,
    ReasonCode,
    worst_state,
)


def test_seven_states_with_documented_names() -> None:
    assert {s.value for s in QualityState} == {
        "UNKNOWN",
        "GOOD",
        "ACCEPTABLE",
        "POOR",
        "INVALID",
        "STALE",
        "MISSING",
    }


def test_nine_reason_codes_partitioned_into_validation_and_signal_quality() -> None:
    assert {r.value for r in ReasonCode} == {
        "malformed_sample",
        "missing",
        "impossible_hr",
        "invalid_timestamp",
        "duplicate_timestamp",
        "out_of_order_timestamp",
        "implausible_jump",
        "gap",
        "stale",
    }
    assert set(ReasonCode) == VALIDATION_REASONS | SIGNAL_QUALITY_REASONS
    assert not VALIDATION_REASONS & SIGNAL_QUALITY_REASONS
    assert len(VALIDATION_REASONS) == 4 and len(SIGNAL_QUALITY_REASONS) == 5


def test_precedence_order_is_the_documented_one() -> None:
    assert [s.value for s in STATE_PRECEDENCE] == [
        "INVALID",
        "MISSING",
        "STALE",
        "POOR",
        "ACCEPTABLE",
        "GOOD",
        "UNKNOWN",
    ]
    assert set(STATE_PRECEDENCE) == set(QualityState)


@pytest.mark.parametrize(("higher", "lower"), list(itertools.combinations(STATE_PRECEDENCE, 2)))
def test_every_pair_resolves_to_the_higher_precedence_state(
    higher: QualityState, lower: QualityState
) -> None:
    assert worst_state([higher, lower]) is higher
    assert worst_state([lower, higher]) is higher


def test_worst_state_of_one_and_of_repeats() -> None:
    for state in QualityState:
        assert worst_state([state]) is state
        assert worst_state([state, state, state]) is state


def test_worst_state_of_nothing_is_an_error_not_a_default() -> None:
    with pytest.raises(ValueError):
        worst_state([])
