"""Sensor abstraction: generic interface, in-memory sample type, simulator and manual input.

Phase 1 contains no vendor adapter, no transport and no persistence.
"""

from interval_assistance.sensors.base import (
    ConnectionStatus,
    HeartRateSensor,
    SensorProvider,
)
from interval_assistance.sensors.manual import ManualHeartRateSensor
from interval_assistance.sensors.sample import HeartRateSample, SourceKind
from interval_assistance.sensors.simulator import (
    SimulationSpeed,
    SimulatorConfig,
    SimulatorHeartRateSensor,
)

__all__ = [
    "ConnectionStatus",
    "HeartRateSample",
    "HeartRateSensor",
    "ManualHeartRateSensor",
    "SensorProvider",
    "SimulationSpeed",
    "SimulatorConfig",
    "SimulatorHeartRateSensor",
    "SourceKind",
]
