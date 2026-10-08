"""Structured logging. Physiological values and identifiers must not appear in logs."""

from __future__ import annotations

import json
import logging
from typing import Any

REDACTED = "[redacted]"

# Extra-field names that may carry physiological or identifying data. Matching is by
# lower-cased name; values are replaced, never emitted.
SENSITIVE_FIELD_NAMES = frozenset(
    {
        "hr",
        "bpm",
        "heart_rate",
        "received_hr",
        "value_bpm",
        "sample",
        "samples",
        "raw_payload",
        "athlete_name",
        "name",
        "email",
        "date_of_birth",
    }
)

_STANDARD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__) | {"message", "asctime", "taskName"}


class SensitiveDataFilter(logging.Filter):
    """Redacts sensitive extra fields on every record before formatting."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__):
            if key not in _STANDARD_ATTRS and key.lower() in SENSITIVE_FIELD_NAMES:
                record.__dict__[key] = REDACTED
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRS:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", fmt: str = "json") -> None:
    handler = logging.StreamHandler()
    handler.addFilter(SensitiveDataFilter())
    if fmt == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
