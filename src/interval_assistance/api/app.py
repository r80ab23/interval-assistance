"""FastAPI application factory. Collaborators are injected so tests are deterministic."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request, Response

from interval_assistance import __version__
from interval_assistance.api.errors import register_error_handlers
from interval_assistance.api.security import (
    DenyAllPrincipalProvider,
    DevelopmentPrincipalProvider,
    PrincipalProvider,
    enforce_default_deny,
)
from interval_assistance.api.v1 import router as v1_router
from interval_assistance.core.clock import Clock, SystemClock
from interval_assistance.core.config import Environment, Settings, get_settings
from interval_assistance.core.ids import IdGenerator, UuidGenerator
from interval_assistance.storage.engine import create_db_engine, create_session_factory

access_logger = logging.getLogger("interval_assistance.access")


def create_app(
    settings: Settings | None = None,
    *,
    clock: Clock | None = None,
    id_generator: IdGenerator | None = None,
    principal_provider: PrincipalProvider | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        engine.dispose()

    # The built-in documentation routes are not APIRoutes and bypass default deny, so they
    # are disabled in production.
    docs_enabled = settings.environment is not Environment.PRODUCTION
    app = FastAPI(
        title="Interval Assistance",
        version=__version__,
        description="Research prototype. Phase 1 foundation: health/status only.",
        dependencies=[Depends(enforce_default_deny)],
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    app.state.settings = settings
    app.state.clock = clock or SystemClock()
    app.state.id_generator = id_generator or UuidGenerator()
    app.state.session_factory = create_session_factory(engine)
    if principal_provider is None:
        principal_provider = (
            DevelopmentPrincipalProvider(settings.dev_identity_role)
            if settings.dev_identity_enabled
            else DenyAllPrincipalProvider()
        )
    app.state.principal_provider = principal_provider

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = app.state.id_generator.new_id()
        request.state.request_id = request_id
        started = app.state.clock.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = str(request_id)
        access_logger.info(
            "request completed",
            extra={
                "request_id": str(request_id),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round((app.state.clock.monotonic() - started) * 1000, 3),
            },
        )
        return response

    register_error_handlers(app)
    app.include_router(v1_router)
    return app
