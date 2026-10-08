from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from interval_assistance.sensors.simulator import SimulatorConfig, generate_values


@given(
    seed=st.integers(),
    low=st.floats(0, 1000),
    span=st.floats(0, 1000),
    step=st.floats(0, 100),
)
def test_values_deterministic_and_within_bounds(
    seed: int, low: float, span: float, step: float
) -> None:
    cfg = SimulatorConfig(
        seed=seed, start_value=low, min_value=low, max_value=low + span, max_step=step
    )
    first = [v for _, v in zip(range(50), generate_values(cfg), strict=False)]
    second = [v for _, v in zip(range(50), generate_values(cfg), strict=False)]
    assert first == second
    assert all(cfg.min_value <= v <= cfg.max_value for v in first)
