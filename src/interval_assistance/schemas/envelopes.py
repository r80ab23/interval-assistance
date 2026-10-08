"""Typed response and error envelopes (API_SPECIFICATION.md sections 2 and 6)."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel


class ResponseMeta(BaseModel):
    request_id: uuid.UUID


class ResponseEnvelope[T](BaseModel):
    data: T
    meta: ResponseMeta


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}
    request_id: uuid.UUID | None = None


class ErrorEnvelope(BaseModel):
    error: ErrorBody
