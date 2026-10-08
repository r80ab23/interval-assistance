"""Health and status payloads. These carry no physiological values."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from interval_assistance.core.auth import Role


class ComponentState(StrEnum):
    OK = "ok"
    UNAVAILABLE = "unavailable"


class HealthData(BaseModel):
    status: ComponentState


class PrincipalInfo(BaseModel):
    role: Role
    is_development_identity: bool


class StatusData(BaseModel):
    service: str
    version: str
    environment: str
    database: ComponentState
    principal: PrincipalInfo
