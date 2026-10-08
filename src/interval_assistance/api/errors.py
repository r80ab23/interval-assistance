"""Exception handlers mapping every failure to the typed error envelope."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from interval_assistance.core.errors import IntervalAssistanceError

logger = logging.getLogger(__name__)

_HTTP_CODES = {404: "not_found", 405: "method_not_allowed"}


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": str(request_id) if request_id else None,
        }
    }
    return JSONResponse(status_code=status_code, content=body)


async def _domain_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, IntervalAssistanceError)
    return error_response(request, exc.http_status, exc.code, exc.message, exc.details)


async def _validation_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # Offending input values are deliberately omitted so they cannot be echoed back.
    errors = [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]
    return error_response(
        request, 422, "validation_error", "request validation failed", {"errors": errors}
    )


async def _http_error(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    return error_response(request, exc.status_code, code, str(exc.detail))


async def _unhandled_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled exception", exc_info=exc)
    return error_response(request, 500, "internal_error", "internal server error")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntervalAssistanceError, _domain_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(Exception, _unhandled_error)
