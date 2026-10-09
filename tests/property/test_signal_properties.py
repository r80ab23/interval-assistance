from __future__ import annotations

import json
import math
import random
import re
from datetime import timedelta
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, localcontext
from typing import Any

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from interval_assistance.core.errors import ConfigurationError
from interval_assistance.signal import (
    STATE_PRECEDENCE,
    QualityState,
    ReasonCode,
    SignalQualityConfig,
    StreamState,
    assess_sample,
    canonical_number,
    worst_state,
)
from interval_assistance.signal.canonical import select_digits
from tests.unit.signal.helpers import DOC_CONFIG_SOURCE, T0, make_config, sample

FINITE = st.floats(allow_nan=False, allow_infinity=False)
ANY_FLOAT = st.floats(allow_nan=True, allow_infinity=True)
SLOW = settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
NUMBER_TEXT = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?")


def oracle(x: float) -> str:
    """Independent oracle: Python digits rendered positionally (informative recipe only)."""
    if x == 0:
        return "0"
    text = format(Decimal(repr(x)), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


@SLOW
@given(FINITE)
def test_canonical_number_matches_oracle_round_trips_and_is_plain(x: float) -> None:
    text = canonical_number(x)
    assert text == oracle(x)
    assert float(text) == x
    assert NUMBER_TEXT.fullmatch(text), text
    assert "e" not in text.lower() and "+" not in text
    assert (text == "0") == (x == 0)
    assert text.startswith("-") == (x < 0)


@SLOW
@given(FINITE.filter(lambda x: x != 0))
def test_digit_selection_is_minimal_and_has_no_trailing_zero(x: float) -> None:
    magnitude = abs(x)
    n, k, s = select_digits(magnitude)
    assert 10 ** (k - 1) <= s < 10**k and s % 10 != 0
    with localcontext() as context:
        context.prec = 900
        assert float(Decimal(s).scaleb(n - k)) == magnitude
        if k > 1:
            # Minimality: neither (k-1)-digit decimal bracketing x round-trips to x.
            exact = Decimal(magnitude)
            q = exact.adjusted() + 1 - (k - 1)
            scaled = exact.scaleb(-q)
            lower, upper = (
                int(scaled.to_integral_value(rounding=ROUND_FLOOR)),
                int(scaled.to_integral_value(rounding=ROUND_CEILING)),
            )
            for candidate in (lower, upper):
                if candidate > 0:
                    assert float(Decimal(candidate).scaleb(q)) != magnitude


@SLOW
@given(st.integers(min_value=-1074, max_value=1023))
def test_powers_of_two_round_trip_and_match_oracle(exponent: int) -> None:
    x = 2.0**exponent
    assert canonical_number(x) == oracle(x)
    assert float(canonical_number(-x)) == -x


@SLOW
@given(st.one_of(ANY_FLOAT, st.integers(min_value=-(10**400), max_value=10**400)))
def test_numeric_config_field_is_accepted_exactly_when_it_is_finite(value: Any) -> None:
    try:
        finite = math.isfinite(float(value))
    except OverflowError:
        finite = False
    data = {**DOC_CONFIG_SOURCE, "max_jump_bpm": value}
    if finite:
        config = SignalQualityConfig.from_mapping(data)
        assert config.max_jump_bpm == float(value)
    else:
        with pytest.raises(ConfigurationError):
            SignalQualityConfig.from_mapping(data)


@SLOW
@given(st.one_of(st.booleans(), st.text(), st.none(), st.lists(st.integers(), max_size=2)))
def test_non_numeric_config_values_are_always_rejected(value: Any) -> None:
    with pytest.raises(ConfigurationError):
        SignalQualityConfig.from_mapping({**DOC_CONFIG_SOURCE, "max_jump_bpm": value})


@SLOW
@given(
    low=FINITE,
    high=FINITE,
    jump=FINITE,
    stale=FINITE,
    gap=FINITE,
    seed=st.integers(),
)
def test_config_hash_is_order_independent_and_text_parses_back_to_the_same_values(
    low: float, high: float, jump: float, stale: float, gap: float, seed: int
) -> None:
    data = {
        **DOC_CONFIG_SOURCE,
        "hr_min_bpm": low,
        "hr_max_bpm": high,
        "max_jump_bpm": jump,
        "stale_after_seconds": stale,
        "gap_after_seconds": gap,
    }
    if not low < high:
        with pytest.raises(ConfigurationError):
            SignalQualityConfig.from_mapping(data)
        return
    config = SignalQualityConfig.from_mapping(data)
    items = list(data.items())
    random.Random(seed).shuffle(items)
    assert SignalQualityConfig.from_mapping(dict(items)).config_hash() == config.config_hash()
    # Numbers are read as binary64 (specification 5.1.1 (a)), so integer-looking text is parsed
    # as float, not as an exact Python int.
    parsed = json.loads(config.canonical_text(), parse_int=float)
    assert parsed["hr_min_bpm"] == low + 0.0 and parsed["gap_after_seconds"] == gap + 0.0
    assert config.canonical_text() == config.canonical_text()


heart_rate = st.one_of(st.none(), ANY_FLOAT)
payload = st.one_of(st.none(), st.binary(max_size=4))
offsets = st.floats(min_value=-1000, max_value=1000, allow_nan=False)


@SLOW
@given(st.lists(st.tuples(heart_rate, payload, offsets), min_size=1, max_size=12))
def test_assessment_is_total_deterministic_and_internally_consistent(
    items: list[tuple[float | None, bytes | None, float]],
) -> None:
    config = make_config()

    def run() -> list[Any]:
        state = StreamState()
        steps = []
        for hr, raw, seconds in items:
            step = assess_sample(
                sample(hr, at=T0 + timedelta(seconds=seconds), raw_payload=raw), state, config
            )
            steps.append(step)
            state = step.next_state
        return steps

    first, second = run(), run()
    assert first == second
    for step in first:
        reasons = step.assessment.reasons
        assert step.assessment.state in set(QualityState)
        assert ReasonCode.GAP not in reasons and ReasonCode.STALE not in reasons
        assert len(set(reasons)) == len(reasons)
        has_validation = any(
            r
            in {
                ReasonCode.MALFORMED_SAMPLE,
                ReasonCode.MISSING,
                ReasonCode.IMPOSSIBLE_HR,
                ReasonCode.INVALID_TIMESTAMP,
            }
            for r in reasons
        )
        if has_validation:
            assert step.assessment.state is QualityState.INVALID
        elif not reasons:
            assert step.assessment.state is config.no_findings_state
        else:
            assert step.assessment.state is worst_state(config.state_by_reason[r] for r in reasons)
        if step.gap is not None:
            assert step.gap.start < step.gap.end


@given(st.lists(st.sampled_from(list(QualityState)), min_size=1, max_size=8))
def test_worst_state_is_order_independent_and_a_member_of_the_input(
    states: list[QualityState],
) -> None:
    result = worst_state(states)
    assert result in states
    assert worst_state(reversed(states)) is result
    assert all(STATE_PRECEDENCE.index(result) <= STATE_PRECEDENCE.index(s) for s in states)
