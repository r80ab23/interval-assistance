"""Authorization boundary (Phase 1: a seam only).

- `PrincipalProvider` is the injection seam; production identity is a later decision.
- `DevelopmentPrincipalProvider` supplies a configured development identity.
- Routes must declare `PUBLIC` or `require_roles(...)`. A route declaring neither is denied
  at request time by `enforce_default_deny` (default deny).
- WebSocket authentication is not implemented; this module is the place it will attach.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from typing import Any

from fastapi import Depends, Request
from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute

from interval_assistance.core.auth import Principal, Role
from interval_assistance.core.config import DEV_IDENTITY_ID
from interval_assistance.core.errors import AuthenticationRequired, PermissionDenied

AUTHZ_POLICY_ATTR = "__ia_authz_policy__"
PUBLIC_POLICY = "public"


class PrincipalProvider(ABC):
    @abstractmethod
    async def authenticate(self, request: Request) -> Principal | None:
        """Return the caller's principal, or None when unauthenticated."""


class DenyAllPrincipalProvider(PrincipalProvider):
    """Used when no identity source is configured: every protected route is unauthenticated."""

    async def authenticate(self, request: Request) -> Principal | None:
        return None


class DevelopmentPrincipalProvider(PrincipalProvider):
    """Always returns one configured identity. Never enabled in production (see Settings)."""

    def __init__(self, role: Role) -> None:
        self._principal = Principal(id=DEV_IDENTITY_ID, role=role, is_development_identity=True)

    async def authenticate(self, request: Request) -> Principal | None:
        return self._principal


def _mark[F: Callable[..., Any]](fn: F, policy: str | frozenset[Role]) -> F:
    setattr(fn, AUTHZ_POLICY_ATTR, policy)
    return fn


async def _public() -> None:
    return None


PUBLIC = Depends(_mark(_public, PUBLIC_POLICY))


def require_roles(*roles: Role) -> Any:
    """Dependency factory: authenticate, then require one of `roles`."""
    if not roles:
        raise ValueError("require_roles needs at least one role")
    allowed = frozenset(roles)

    async def _require(request: Request) -> Principal:
        provider: PrincipalProvider = request.app.state.principal_provider
        principal = await provider.authenticate(request)
        if principal is None:
            raise AuthenticationRequired("authentication is required")
        if principal.role not in allowed:
            raise PermissionDenied("the current role may not access this resource")
        request.state.principal = principal
        return principal

    return Depends(_mark(_require, allowed))


def _calls(dependant: Dependant) -> Iterable[Callable[..., Any]]:
    for dep in dependant.dependencies:
        if dep.call is not None:
            yield dep.call
        yield from _calls(dep)


def declared_policy(route: APIRoute) -> list[str | frozenset[Role]]:
    return [
        getattr(call, AUTHZ_POLICY_ATTR)
        for call in _calls(route.dependant)
        if hasattr(call, AUTHZ_POLICY_ATTR)
    ]


async def enforce_default_deny(request: Request) -> None:
    """App-level dependency: reject any route that declares no authorization policy."""
    route = request.scope.get("route")
    if not isinstance(route, APIRoute) or not declared_policy(route):
        raise PermissionDenied("no authorization policy is declared for this route")
