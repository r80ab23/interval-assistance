from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from interval_assistance.core.clock import ManualClock
from interval_assistance.core.errors import SensorConnectionError
from interval_assistance.sensors import (
    ConnectionStatus,
    HeartRateSample,
    ManualHeartRateSensor,
    SensorProvider,
    SimulationSpeed,
    SimulatorConfig,
    SimulatorHeartRateSensor,
    SourceKind,
)
from interval_assistance.sensors.simulator import generate_values

SENSOR_ID = uuid.UUID(int=7)
T0 = datetime(2026, 1, 1, tzinfo=UTC)


def config(**overrides: object) -> SimulatorConfig:
    values: dict[str, object] = {
        "seed": 42,
        "start_value": 100.0,
        "min_value": 50.0,
        "max_value": 150.0,
        "max_step": 5.0,
    }
    values.update(overrides)
    return SimulatorConfig(**values)  # type: ignore[arg-type]


async def no_sleep(_seconds: float) -> None:
    return None


async def collect(sensor: SimulatorHeartRateSensor) -> list[HeartRateSample]:
    await sensor.connect()
    await sensor.start()
    return [s async for s in sensor.samples()]


def test_generator_is_deterministic_and_bounded() -> None:
    cfg = config()
    a = [v for _, v in zip(range(200), generate_values(cfg), strict=False)]
    b = [v for _, v in zip(range(200), generate_values(cfg), strict=False)]
    assert a == b
    assert all(cfg.min_value <= v <= cfg.max_value for v in a)
    other = [v for _, v in zip(range(200), generate_values(config(seed=43)), strict=False)]
    assert a != other


def test_config_validation() -> None:
    with pytest.raises(ValueError):
        config(start_value=10.0)
    with pytest.raises(ValueError):
        config(max_step=-1.0)
    with pytest.raises(ValueError):
        config(interval_seconds=0.0)


async def test_simulator_stream_is_reproducible_and_synthetic() -> None:
    def build() -> SimulatorHeartRateSensor:
        return SimulatorHeartRateSensor(
            config(), ManualClock(T0), SENSOR_ID, sleep=no_sleep, max_samples=10
        )

    first, second = await collect(build()), await collect(build())
    assert first == second
    assert len(first) == 10
    assert all(s.is_synthetic and s.source_kind is SourceKind.SIMULATED for s in first)
    assert [s.received_at.timestamp() - T0.timestamp() for s in first] == list(range(10))


async def test_simulator_speed_scales_pacing_only() -> None:
    pauses: dict[int, list[float]] = {}
    for speed in SimulationSpeed:
        recorded: list[float] = []

        async def record(seconds: float, sink: list[float] = recorded) -> None:
            sink.append(seconds)

        sensor = SimulatorHeartRateSensor(
            config(speed=speed), ManualClock(T0), SENSOR_ID, sleep=record, max_samples=3
        )
        await collect(sensor)
        pauses[int(speed)] = recorded
    assert pauses[1] == [1.0] * 3
    assert pauses[5] == [0.2] * 3
    assert pauses[20] == [0.05] * 3


async def test_simulator_lifecycle() -> None:
    sensor = SimulatorHeartRateSensor(config(), ManualClock(T0), SENSOR_ID, sleep=no_sleep)
    assert sensor.status is ConnectionStatus.DISCONNECTED
    with pytest.raises(SensorConnectionError):
        await sensor.start()
    await sensor.connect()
    assert sensor.status.value == "connected"
    await sensor.start()
    assert sensor.status.value == "streaming"
    await sensor.stop()
    assert sensor.status.value == "connected"
    await sensor.disconnect()
    assert sensor.status.value == "disconnected"


async def test_simulator_samples_require_streaming() -> None:
    sensor = SimulatorHeartRateSensor(config(), ManualClock(T0), SENSOR_ID, sleep=no_sleep)
    with pytest.raises(SensorConnectionError):
        _ = [s async for s in sensor.samples()]


async def test_manual_sensor_flags_and_clock_stamping() -> None:
    clock = ManualClock(T0)
    sensor = ManualHeartRateSensor(clock, SENSOR_ID)
    with pytest.raises(SensorConnectionError):
        sensor.submit(100)
    await sensor.connect()
    await sensor.start()
    sensor.submit(101)
    clock.advance(2)
    sensor.submit(99.5)
    await sensor.stop()
    got = [s async for s in sensor.samples()]
    assert [s.received_hr for s in got] == [101, 99.5]
    assert got[1].received_at == clock.now_utc()
    assert all(s.is_synthetic and s.source_kind is SourceKind.MANUAL for s in got)


async def test_manual_sensor_restart_keeps_new_run_samples() -> None:
    """A stop marker left over from a previous run must not end the next run's stream."""
    sensor = ManualHeartRateSensor(ManualClock(T0), SENSOR_ID)
    await sensor.connect()
    await sensor.start()
    await sensor.stop()  # no consumer drains the queue here
    await sensor.start()
    sensor.submit(100)

    stream = sensor.samples()
    first = await anext(stream)
    assert first.received_hr == 100

    sensor.submit(101)
    await sensor.stop()
    rest = [s async for s in stream]
    assert [s.received_hr for s in rest] == [101]


async def test_manual_sensor_second_run_ends_only_at_its_own_stop() -> None:
    sensor = ManualHeartRateSensor(ManualClock(T0), SENSOR_ID)
    await sensor.connect()
    for value in (1, 2):
        await sensor.start()
        sensor.submit(value)
        await sensor.stop()
    got = [s.received_hr for s in [x async for x in sensor.samples()]]
    assert got == [1, 2]


def test_sample_invariants() -> None:
    with pytest.raises(ValueError):
        HeartRateSample(SENSOR_ID, SourceKind.REAL, False, 1.0, datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        HeartRateSample(SENSOR_ID, SourceKind.MANUAL, False, 1.0, T0)
    HeartRateSample(SENSOR_ID, SourceKind.REAL, False, 1.0, T0)


def test_provider_registry() -> None:
    provider = SensorProvider()
    provider.register("manual", lambda: ManualHeartRateSensor(ManualClock(T0), SENSOR_ID))
    assert provider.names() == ["manual"]
    assert provider.create("manual").source_kind is SourceKind.MANUAL
    with pytest.raises(ValueError):
        provider.register("manual", lambda: ManualHeartRateSensor(ManualClock(T0), SENSOR_ID))
    with pytest.raises(SensorConnectionError):
        provider.create("polar_h10")
