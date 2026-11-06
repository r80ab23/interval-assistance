"""Stream-hash conformance: explicit expected bytes, not a JSON-library oracle."""

import hashlib
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from interval_assistance.ingestion.replay_fixture import canonical_stream, stream_hash
from tests.unit.signal.helpers import sample


def test_fixed_vector() -> None:
    expected = (
        b'{"format":"replay-fixture-stream/1","samples":['
        b'{"adapter_quality_hint":null,"device_timestamp":null,"is_synthetic":true,'
        b'"raw_payload":null,"received_at":"2026-01-01T12:00:00.000000Z",'
        b'"received_hr":"f64:402e000000000000"}]}'
    )
    assert canonical_stream([sample(15)]) == expected
    digest = "c0c61c4734d60d83e4b9518aef9d45efa63cd88146e4d50a311e483c8eea7f9f"
    assert hashlib.sha256(expected).hexdigest() == digest
    assert stream_hash([sample(15)]) == digest


@pytest.mark.parametrize(
    ("value", "encoded"),
    [
        (0.0, "f64:0000000000000000"),
        (-0.0, "f64:8000000000000000"),
        (5e-324, "f64:0000000000000001"),
        (float.fromhex("0x1.fffffffffffffp+1023"), "f64:7fefffffffffffff"),
        (float("nan"), "nan"),
        (math.inf, "+inf"),
        (-math.inf, "-inf"),
        (None, None),
    ],
)
def test_number_classes(value: float | None, encoded: str | None) -> None:
    assert json.loads(canonical_stream([sample(value)]))["samples"][0]["received_hr"] == encoded


def test_strings_and_payload() -> None:
    item = replace(sample(raw_payload=b"\x00\xff"), quality_hint=' a\t\n"\\\u00e9 ')
    data = canonical_stream([item])
    assert b' a\\u0009\\u000a\\"\\\\\xc3\xa9 ' in data
    assert json.loads(data)["samples"][0]["raw_payload"] == "AP8="
    assert not data.endswith(b"\n")
    with pytest.raises(ValueError, match="Unicode"):
        canonical_stream([replace(item, quality_hint="\ud800")])


def test_checked_in_fixture_metadata() -> None:
    from datetime import datetime, timedelta
    from itertools import islice

    from interval_assistance.ingestion.replay_fixture import STREAM_FORMAT
    from interval_assistance.sensors.simulator import SimulatorConfig, generate_values

    path = Path(__file__).resolve().parents[3] / "data/synthetic/replay-basic.fixture.json"
    metadata = json.loads(path.read_text())
    assert metadata["is_synthetic"] is True and metadata["generator"] == "simulator"
    assert metadata["stream_hash_format"] == STREAM_FORMAT
    config = SimulatorConfig(**metadata["parameters"])
    start = datetime.fromisoformat(metadata["clock_start_utc"])
    samples = [
        sample(value, at=start + timedelta(seconds=i * config.interval_seconds))
        for i, value in enumerate(islice(generate_values(config), metadata["sample_count"]))
    ]
    assert stream_hash(samples) == metadata["stream_sha256"]
