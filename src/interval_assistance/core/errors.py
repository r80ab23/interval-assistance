"""Structured domain errors. Errors are never swallowed or used to mask invalid data."""

from __future__ import annotations

from typing import Any


class IntervalAssistanceError(Exception):
    """Base class. `code` is a stable machine code; `http_status` is the API mapping."""

    code: str = "internal_error"
    http_status: int = 500

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details or {}


class ConfigurationError(IntervalAssistanceError):
    code = "configuration_error"


class AuthenticationRequired(IntervalAssistanceError):
    code = "authentication_required"
    http_status = 401


class PermissionDenied(IntervalAssistanceError):
    code = "permission_denied"
    http_status = 403


class SensorConnectionError(IntervalAssistanceError):
    """Sensor connection/lifecycle failure. HTTP mapping is OPEN (API_SPECIFICATION.md 6)."""

    code = "sensor_connection_error"
