from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Annotated

import pytest
from fastapi import APIRouter
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from interval_assistance.api.app import create_app
from interval_assistance.api.security import PUBLIC, declared_policy, require_roles
from interval_assistance.core.auth import Principal, Role
from interval_assistance.core.clock import ManualClock
from interval_assistance.core.ids import SequentialIdGenerator
from tests.conftest import T0, make_settings


def test_health_is_public(client: TestClient) -> None:
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["data"] == {"status": "ok"}
    assert uuid.UUID(body["meta"]["request_id"]) == uuid.UUID(res.headers["X-Request-ID"])


def test_request_ids_are_deterministic_with_injected_generator(client: TestClient) -> None:
    ids = [client.get("/api/v1/health").json()["meta"]["request_id"] for _ in range(2)]
    assert ids == [str(uuid.UUID(int=1)), str(uuid.UUID(int=2))]


def test_status_with_dev_identity(client: TestClient) -> None:
    res = client.get("/api/v1/status")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["service"] == "interval-assistance"
    assert data["database"] == "ok"
    assert data["environment"] == "test"
    assert data["principal"] == {"role": "coach", "is_development_identity": True}


def test_status_without_identity_is_401_envelope(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, dev_identity=False), clock=ManualClock(T0))
    with TestClient(app) as c:
        res = c.get("/api/v1/status")
    assert res.status_code == 401
    err = res.json()["error"]
    assert err["code"] == "authentication_required"
    assert err["request_id"]


def test_each_role_is_accepted(tmp_path: Path) -> None:
    for role in Role:
        app = create_app(make_settings(tmp_path, role=role))
        with TestClient(app) as c:
            assert c.get("/api/v1/status").json()["data"]["principal"]["role"] == role.value


def test_unknown_route_uses_error_envelope(client: TestClient) -> None:
    res = client.get("/api/v1/nope")
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "not_found"


def test_wrong_method_uses_error_envelope(client: TestClient) -> None:
    res = client.post("/api/v1/health")
    assert res.status_code == 405
    assert res.json()["error"]["code"] == "method_not_allowed"


def test_route_without_policy_is_denied_by_default(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    router = APIRouter()

    @router.get("/undeclared")
    def undeclared() -> dict[str, str]:
        return {"x": "y"}

    app.include_router(router)
    with TestClient(app) as c:
        res = c.get("/undeclared")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "permission_denied"


def test_unhandled_exception_returns_generic_500_envelope(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    app = create_app(make_settings(tmp_path), id_generator=SequentialIdGenerator(5))
    router = APIRouter()

    @router.get("/boom", dependencies=[PUBLIC])
    def boom() -> None:
        raise RuntimeError("secret detail 150 bpm")

    app.include_router(router)
    with caplog.at_level(logging.ERROR), TestClient(app, raise_server_exceptions=False) as c:
        res = c.get("/boom")

    assert res.status_code == 500
    assert res.json() == {
        "error": {
            "code": "internal_error",
            "message": "internal server error",
            "details": {},
            "request_id": str(uuid.UUID(int=5)),
        }
    }
    assert "secret detail" not in res.text and "RuntimeError" not in res.text
    # The failure is still recorded server-side with its traceback.
    records = [r for r in caplog.records if r.name == "interval_assistance.api.errors"]
    assert len(records) == 1 and records[0].exc_info is not None


def test_role_not_permitted_is_denied_with_error_envelope(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, role=Role.ATHLETE))
    router = APIRouter()

    @router.get("/coach-only")
    def coach_only(_: Annotated[Principal, require_roles(Role.COACH)]) -> dict[str, str]:
        return {"reached": "handler"}

    app.include_router(router)
    with TestClient(app) as c:
        res = c.get("/coach-only")

    assert res.status_code == 403
    body = res.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == "permission_denied"
    assert body["error"]["request_id"]
    assert "reached" not in res.text
    # The response does not reveal which role would be accepted.
    assert "coach" not in res.text.lower()


def test_permitted_role_reaches_the_same_route(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path, role=Role.COACH))
    router = APIRouter()

    @router.get("/coach-only")
    def coach_only(_: Annotated[Principal, require_roles(Role.COACH)]) -> dict[str, str]:
        return {"reached": "handler"}

    app.include_router(router)
    with TestClient(app) as c:
        assert c.get("/coach-only").json() == {"reached": "handler"}


def _api_routes(router: object) -> list[APIRoute]:
    """Collect APIRoutes, descending into included routers (FastAPI wraps them lazily)."""
    found: list[APIRoute] = []
    for route in getattr(router, "routes", []):
        if isinstance(route, APIRoute):
            found.append(route)
        elif hasattr(route, "original_router"):
            found.extend(_api_routes(route.original_router))
    return found


def test_every_api_route_declares_a_policy(tmp_path: Path) -> None:
    from interval_assistance.api.v1 import router as v1_router

    routes = _api_routes(v1_router)
    assert {r.path for r in routes} == {"/health", "/status"}
    for route in routes:
        assert declared_policy(route), f"{route.path} declares no authorization policy"


def test_phase_1_exposes_only_health_and_status(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    assert set(app.openapi()["paths"]) == {"/api/v1/health", "/api/v1/status"}
    assert not any("websocket" in type(r).__name__.lower() for r in app.routes)


def test_validation_errors_do_not_echo_input(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    router = APIRouter()
    from interval_assistance.api.security import PUBLIC

    @router.get("/echo", dependencies=[PUBLIC])
    def echo(n: int) -> int:
        return n

    app.include_router(router)
    with TestClient(app) as c:
        res = c.get("/echo", params={"n": "123-not-a-number"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "validation_error"
    assert "123-not-a-number" not in res.text


def test_ids_injected(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path), id_generator=SequentialIdGenerator(10))
    with TestClient(app) as c:
        assert c.get("/api/v1/health").json()["meta"]["request_id"] == str(uuid.UUID(int=10))


def test_documentation_routes_are_disabled_in_production(tmp_path: Path) -> None:
    from interval_assistance.core.config import Environment

    # model_copy skips validation: the SQLite URL only avoids needing a PostgreSQL driver here.
    settings = make_settings(tmp_path, dev_identity=False).model_copy(
        update={"environment": Environment.PRODUCTION}
    )
    app = create_app(settings)
    assert app.openapi_url is None and app.docs_url is None and app.redoc_url is None
