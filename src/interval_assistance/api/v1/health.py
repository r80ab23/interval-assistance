"""Health (public liveness) and status (authenticated) endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from interval_assistance import __version__
from interval_assistance.api.deps import get_request_id, get_session, get_settings_dep
from interval_assistance.api.security import PUBLIC, require_roles
from interval_assistance.core.auth import Principal, Role
from interval_assistance.core.config import Settings
from interval_assistance.schemas.envelopes import ErrorEnvelope, ResponseEnvelope, ResponseMeta
from interval_assistance.schemas.health import (
    ComponentState,
    HealthData,
    PrincipalInfo,
    StatusData,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

_AUTH_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorEnvelope},
    403: {"model": ErrorEnvelope},
}


@router.get("/health", dependencies=[PUBLIC])
def health(
    request_id: Annotated[uuid.UUID, Depends(get_request_id)],
) -> ResponseEnvelope[HealthData]:
    """Liveness only: the process is serving requests."""
    return ResponseEnvelope(
        data=HealthData(status=ComponentState.OK), meta=ResponseMeta(request_id=request_id)
    )


@router.get("/status", responses=_AUTH_ERRORS)
def status(
    principal: Annotated[Principal, require_roles(Role.COACH, Role.ATHLETE, Role.RESEARCHER)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
    session: Annotated[Session, Depends(get_session)],
    request_id: Annotated[uuid.UUID, Depends(get_request_id)],
) -> ResponseEnvelope[StatusData]:
    """Service status including database connectivity and the caller's role."""
    try:
        session.execute(text("SELECT 1"))
        database = ComponentState.OK
    except SQLAlchemyError:
        logger.warning("database check failed")
        database = ComponentState.UNAVAILABLE
    return ResponseEnvelope(
        data=StatusData(
            service="interval-assistance",
            version=__version__,
            environment=settings.environment.value,
            database=database,
            principal=PrincipalInfo(
                role=principal.role,
                is_development_identity=principal.is_development_identity,
            ),
        ),
        meta=ResponseMeta(request_id=request_id),
    )
