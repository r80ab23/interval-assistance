"""Canonical generated-stream bytes for synthetic replay fixtures (TESTING_STRATEGY 6)."""

from __future__ import annotations

import base64
import hashlib
import math
import struct
from collections.abc import Iterable
from datetime import datetime

from interval_assistance.ingestion.mapping import to_utc
from interval_assistance.sensors.sample import HeartRateSample

STREAM_FORMAT = "replay-fixture-stream/1"


def _string(value: str) -> str:
    parts = ['"']
    for char in value:
        number = ord(char)
        if 0xD800 <= number <= 0xDFFF:
            raise ValueError("invalid Unicode scalar")
        if number < 32:
            parts.append(f"\\u{number:04x}")
        elif char in ('"', "\\"):
            parts.append("\\" + char)
        else:
            parts.append(char)
    return "".join(parts) + '"'


def _timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.utcoffset() is None:
        raise ValueError("fixture timestamp must be aware")
    return to_utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _hr(value: float | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("boolean HR is not a fixture number")
    number = float(value)
    if math.isnan(number):
        return "nan"
    if math.isinf(number):
        return "+inf" if number > 0 else "-inf"
    return "f64:" + struct.pack(">d", number).hex()


def canonical_stream(samples: Iterable[HeartRateSample]) -> bytes:
    rows = []
    for sample in samples:
        document: dict[str, str | bool | None] = {
            "received_hr": _hr(sample.received_hr),
            "received_at": _timestamp(sample.received_at),
            "device_timestamp": _timestamp(sample.device_timestamp),
            "raw_payload": (
                None
                if sample.raw_payload is None
                else base64.b64encode(sample.raw_payload).decode("ascii")
            ),
            "adapter_quality_hint": sample.quality_hint,
            "is_synthetic": sample.is_synthetic,
        }
        fields = []
        for key, value in sorted(document.items()):
            encoded = (
                "null"
                if value is None
                else "true"
                if value is True
                else "false"
                if value is False
                else _string(value)
            )
            fields.append(_string(key) + ":" + encoded)
        rows.append("{" + ",".join(fields) + "}")
    return ('{"format":' + _string(STREAM_FORMAT) + ',"samples":[' + ",".join(rows) + "]}").encode(
        "utf-8"
    )


def stream_hash(samples: Iterable[HeartRateSample]) -> str:
    return hashlib.sha256(canonical_stream(samples)).hexdigest()
