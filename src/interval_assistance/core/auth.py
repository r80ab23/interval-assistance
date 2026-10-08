"""Authorization vocabulary: roles and the authenticated principal.

Phase 1 is an architectural boundary only: no login, password store, identity provider or JWT.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    COACH = "coach"
    ATHLETE = "athlete"
    RESEARCHER = "researcher"


@dataclass(frozen=True, slots=True)
class Principal:
    id: uuid.UUID
    role: Role
    is_development_identity: bool = False
