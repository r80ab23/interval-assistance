"""Regression: an int too large for a float must not leak OverflowError from validation or
quality assessment. Such a number is finite and beyond every configured bound."""

from __future__ import annotations

import pytest

from interval_assistance.signal import (
    QualityState,
    ReasonCode,
    StreamState,
    assess_sample,
    validate_sample,
)
from interval_assistance.signal.validation import is_finite_number

from .helpers import T0, make_config, sample

CONFIG = make_config()  # hr bounds [10, 20], max_jump_bpm 5 (test conventions)
HUGE = [10**400, -(10**400)]


@pytest.mark.parametrize("value", HUGE)
def test_huge_ints_are_finite_numbers(value: int) -> None:
    assert is_finite_number(value) is True


@pytest.mark.parametrize("value", HUGE)
def test_huge_ints_are_impossible_hr_not_malformed(value: int) -> None:
    findings = validate_sample(sample(value), CONFIG)
    assert findings == (ReasonCode.IMPOSSIBLE_HR,)


@pytest.mark.parametrize("value", HUGE)
def test_assessment_of_a_huge_int_is_invalid_without_overflow(value: int) -> None:
    first = assess_sample(sample(15.0), StreamState(), CONFIG)
    step = assess_sample(sample(value, seconds=1), first.next_state, CONFIG)
    assert step.assessment.state is QualityState.INVALID
    assert step.assessment.reasons[0] is ReasonCode.IMPOSSIBLE_HR
    # The difference from the previous value is beyond any finite limit.
    assert ReasonCode.IMPLAUSIBLE_JUMP in step.assessment.reasons
    # The invalid value does not become the reference for later jumps.
    assert step.next_state.last_valid_hr == 15.0


def test_a_huge_int_as_first_sample_has_no_jump_reference() -> None:
    step = assess_sample(sample(10**400), StreamState(), CONFIG)
    assert step.assessment.reasons == (ReasonCode.IMPOSSIBLE_HR,)
    assert step.next_state.max_received_at == T0
