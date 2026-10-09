from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from interval_assistance.signal import (
    QualityState,
    ReasonCode,
    StreamState,
    assess_sample,
    effective_timestamp,
    evaluate_stale,
)

from .helpers import DOC_CONFIG_SOURCE, T0, make_config, sample

CONFIG = make_config()  # jump 5, gap 7 s, stale 3.5 s, no_findings GOOD (test conventions)
EMPTY = StreamState()


def state_map(**mapping: str) -> dict[str, str]:
    return {**DOC_CONFIG_SOURCE["state_by_reason"], **mapping}


def run(samples: list[object], config=CONFIG):  # type: ignore[no-untyped-def]
    state = EMPTY
    steps = []
    for item in samples:
        step = assess_sample(item, state, config)  # type: ignore[arg-type]
        steps.append(step)
        state = step.next_state
    return steps


def test_first_sample_has_no_stateful_findings_and_gets_no_findings_state() -> None:
    step = assess_sample(sample(15.0), EMPTY, CONFIG)
    assert step.assessment.reasons == () and step.assessment.state is QualityState.GOOD
    assert step.gap is None


@pytest.mark.parametrize("state", list(QualityState))
def test_no_findings_state_comes_only_from_configuration(state: QualityState) -> None:
    config = make_config(no_findings_state=state.value)
    step = assess_sample(sample(15.0), EMPTY, config)
    assert step.assessment.state is state and step.assessment.reasons == ()


def test_duplicate_timestamp_uses_the_configured_state() -> None:
    steps = run([sample(15.0, seconds=0), sample(15.0, seconds=0)])
    assert steps[1].assessment.reasons == (ReasonCode.DUPLICATE_TIMESTAMP,)
    assert steps[1].assessment.state is QualityState.POOR


def test_out_of_order_timestamp_uses_the_configured_state() -> None:
    steps = run([sample(15.0, seconds=5), sample(15.0, seconds=4)])
    assert steps[1].assessment.reasons == (ReasonCode.OUT_OF_ORDER_TIMESTAMP,)
    assert steps[1].assessment.state is QualityState.POOR


def test_in_order_samples_have_no_timestamp_finding() -> None:
    assert run([sample(15.0, seconds=0), sample(15.0, seconds=1)])[1].assessment.reasons == ()


def test_timestamp_comparison_uses_the_previous_sample_not_the_maximum() -> None:
    steps = run([sample(15.0, seconds=5), sample(15.0, seconds=4), sample(15.0, seconds=4.5)])
    assert steps[2].assessment.reasons == ()  # later than the previous (4), though below 5


def test_device_timestamp_is_used_when_present_and_valid() -> None:
    later = T0 + timedelta(seconds=30)
    steps = run(
        [
            sample(15.0, seconds=0, device_timestamp=later),
            sample(15.0, seconds=1, device_timestamp=later),
        ]
    )
    assert steps[1].assessment.reasons == (ReasonCode.DUPLICATE_TIMESTAMP,)


def test_naive_device_timestamp_falls_back_to_received_at_and_is_invalid() -> None:
    naive = datetime(1999, 1, 1)
    step = run([sample(15.0, seconds=0), sample(15.0, seconds=1, device_timestamp=naive)])[1]
    assert step.assessment.reasons == (ReasonCode.INVALID_TIMESTAMP,)
    assert step.assessment.state is QualityState.INVALID
    assert effective_timestamp(sample(15.0, seconds=1, device_timestamp=naive)) == T0 + timedelta(
        seconds=1
    )


def test_non_utc_offsets_are_compared_as_instants() -> None:
    plus3 = timezone(timedelta(hours=3))
    first = sample(15.0, seconds=0, device_timestamp=datetime(2026, 1, 1, 15, 0, 5, tzinfo=plus3))
    same_instant = sample(
        15.0, seconds=1, device_timestamp=datetime(2026, 1, 1, 12, 0, 5, tzinfo=UTC)
    )
    assert run([first, same_instant])[1].assessment.reasons == (ReasonCode.DUPLICATE_TIMESTAMP,)
    assert effective_timestamp(first) == datetime(2026, 1, 1, 12, 0, 5, tzinfo=UTC)
    assert effective_timestamp(first).utcoffset() == timedelta(0)


def test_mixed_axes_are_compared_literally() -> None:
    # Documented literal reading: effective timestamps are compared whichever axis each used.
    steps = run(
        [
            sample(15.0, seconds=10),
            sample(15.0, seconds=11, device_timestamp=T0),  # device time earlier than 10 s
        ]
    )
    assert steps[1].assessment.reasons == (ReasonCode.OUT_OF_ORDER_TIMESTAMP,)


def test_implausible_jump_boundary_is_strictly_greater() -> None:
    at_limit = run([sample(10.0, seconds=0), sample(15.0, seconds=1)])[1]
    assert at_limit.assessment.reasons == ()
    over = run([sample(10.0, seconds=0), sample(15.5, seconds=1)])[1]
    assert over.assessment.reasons == (ReasonCode.IMPLAUSIBLE_JUMP,)
    assert over.assessment.state is QualityState.POOR
    down = run([sample(18.0, seconds=0), sample(12.0, seconds=1)])[1]
    assert down.assessment.reasons == (ReasonCode.IMPLAUSIBLE_JUMP,)


def test_jump_is_measured_from_the_last_validation_passing_value() -> None:
    steps = run(
        [
            sample(12.0, seconds=0),
            sample(None, seconds=1),  # missing: fails validation
            sample(99.0, seconds=2),  # impossible_hr: fails validation, does not become the base
            sample(14.0, seconds=3),  # 2 away from 12.0: no jump
            sample(20.0, seconds=4),  # 6 away from 14.0: jump
        ]
    )
    assert steps[3].assessment.reasons == ()
    assert steps[4].assessment.reasons == (ReasonCode.IMPLAUSIBLE_JUMP,)


def test_no_jump_without_a_previous_valid_value_or_a_finite_current_value() -> None:
    assert run([sample(None, seconds=0), sample(15.0, seconds=1)])[1].assessment.reasons == ()
    nan_step = run([sample(15.0, seconds=0), sample(float("nan"), seconds=1)])[1]
    assert nan_step.assessment.reasons == (ReasonCode.MALFORMED_SAMPLE,)


def test_any_validation_finding_makes_the_sample_invalid_whatever_the_configuration() -> None:
    config = make_config(no_findings_state="GOOD", state_by_reason=state_map(gap="GOOD"))
    step = assess_sample(sample(99.0), EMPTY, config)
    assert step.assessment.state is QualityState.INVALID
    assert step.assessment.reasons == (ReasonCode.IMPOSSIBLE_HR,)


def test_validation_and_signal_quality_findings_are_both_reported_invalid_dominates() -> None:
    steps = run([sample(12.0, seconds=0), sample(99.0, seconds=0)])
    assert steps[1].assessment.reasons == (
        ReasonCode.IMPOSSIBLE_HR,
        ReasonCode.DUPLICATE_TIMESTAMP,
        ReasonCode.IMPLAUSIBLE_JUMP,
    )
    assert steps[1].assessment.state is QualityState.INVALID


@pytest.mark.parametrize(
    ("duplicate_state", "jump_state", "expected"),
    [
        ("POOR", "ACCEPTABLE", QualityState.POOR),
        ("ACCEPTABLE", "POOR", QualityState.POOR),
        ("GOOD", "ACCEPTABLE", QualityState.ACCEPTABLE),
        ("UNKNOWN", "GOOD", QualityState.GOOD),
        ("STALE", "POOR", QualityState.STALE),
        ("MISSING", "STALE", QualityState.MISSING),
        ("INVALID", "MISSING", QualityState.INVALID),
        ("POOR", "POOR", QualityState.POOR),
    ],
)
def test_several_signal_quality_findings_take_the_highest_precedence_state(
    duplicate_state: str, jump_state: str, expected: QualityState
) -> None:
    config = make_config(
        state_by_reason=state_map(duplicate_timestamp=duplicate_state, implausible_jump=jump_state)
    )
    steps = run([sample(10.0, seconds=0), sample(19.0, seconds=0)], config)
    assert steps[1].assessment.reasons == (
        ReasonCode.DUPLICATE_TIMESTAMP,
        ReasonCode.IMPLAUSIBLE_JUMP,
    )
    assert steps[1].assessment.state is expected


@pytest.mark.parametrize("state", list(QualityState))
def test_a_single_finding_takes_exactly_its_configured_state(state: QualityState) -> None:
    config = make_config(state_by_reason=state_map(out_of_order_timestamp=state.value))
    step = run([sample(15.0, seconds=5), sample(15.0, seconds=4)], config)[1]
    assert step.assessment.state is state


def test_gap_is_a_closed_range_between_receive_times_not_a_sample_reason() -> None:
    steps = run([sample(15.0, seconds=0), sample(15.0, seconds=7.5)])
    gap = steps[1].gap
    assert gap is not None
    assert (gap.reason, gap.state) == (ReasonCode.GAP, QualityState.MISSING)
    assert (gap.start, gap.end) == (T0, T0 + timedelta(seconds=7.5))
    assert steps[1].assessment.reasons == () and steps[1].assessment.state is QualityState.GOOD


def test_gap_boundary_is_strictly_greater_and_ignores_reversed_time() -> None:
    assert run([sample(15.0, seconds=0), sample(15.0, seconds=7.0)])[1].gap is None
    assert run([sample(15.0, seconds=0), sample(15.0, seconds=7.000001)])[1].gap is not None
    assert run([sample(15.0, seconds=100), sample(15.0, seconds=0)])[1].gap is None


def test_gap_uses_every_arrival_including_invalid_samples() -> None:
    steps = run([sample(15.0, seconds=0), sample(None, seconds=6), sample(15.0, seconds=12)])
    assert steps[1].gap is None and steps[2].gap is None  # 6 s then 6 s: no gap of > 7 s


def test_gap_state_comes_from_configuration() -> None:
    config = make_config(state_by_reason=state_map(gap="POOR"))
    gap = run([sample(15.0, seconds=0), sample(15.0, seconds=60)], config)[1].gap
    assert gap is not None and gap.state is QualityState.POOR


def test_stream_state_tracks_the_previous_sample() -> None:
    steps = run([sample(12.0, seconds=0), sample(None, seconds=1), sample(14.0, seconds=2)])
    first, second, third = (s.next_state for s in steps)
    assert (first.last_timestamp, first.last_received_at, first.last_valid_hr) == (T0, T0, 12.0)
    assert second.last_valid_hr == 12.0 and second.last_received_at == T0 + timedelta(seconds=1)
    assert third.last_valid_hr == 14.0


def test_assessment_is_deterministic_and_does_not_mutate_state() -> None:
    state = StreamState(last_timestamp=T0, last_received_at=T0, last_valid_hr=12.0)
    item = sample(19.0, seconds=0)
    first = assess_sample(item, state, CONFIG)
    second = assess_sample(item, state, CONFIG)
    assert first == second
    assert state == StreamState(last_timestamp=T0, last_received_at=T0, last_valid_hr=12.0)


def test_stale_boundary_is_strictly_greater_and_pure() -> None:
    assert evaluate_stale(T0, T0 + timedelta(seconds=3.5), CONFIG) is None
    finding = evaluate_stale(T0, T0 + timedelta(seconds=3.6), CONFIG)
    assert finding is not None
    assert (finding.reason, finding.state) == (ReasonCode.STALE, QualityState.STALE)
    assert (finding.start, finding.end) == (T0, T0 + timedelta(seconds=3.6))
    assert evaluate_stale(T0, T0 + timedelta(seconds=3.6), CONFIG) == finding


def test_stale_state_comes_from_configuration() -> None:
    config = make_config(state_by_reason=state_map(stale="MISSING"))
    finding = evaluate_stale(T0, T0 + timedelta(seconds=10), config)
    assert finding is not None and finding.state is QualityState.MISSING


def test_stale_normalizes_offsets_and_requires_aware_times() -> None:
    plus3 = timezone(timedelta(hours=3))
    finding = evaluate_stale(
        T0.astimezone(plus3), (T0 + timedelta(seconds=10)).astimezone(plus3), CONFIG
    )
    assert finding is not None and finding.start.utcoffset() == timedelta(0)
    with pytest.raises(ValueError):
        evaluate_stale(datetime(2026, 1, 1), T0, CONFIG)
    with pytest.raises(ValueError):
        evaluate_stale(T0, datetime(2026, 1, 1), CONFIG)
