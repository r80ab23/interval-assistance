"""The `ingestion` layer contracts exist in pyproject.toml and no lower layer imports it."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "interval_assistance"
LOWER_LAYERS = ("core", "sensors", "signal", "storage", "schemas")


def _contracts() -> dict[str, dict[str, Any]]:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return {c["name"]: c for c in data["tool"]["importlinter"]["contracts"]}


def test_contracts_forbid_lower_layers_from_importing_ingestion() -> None:
    contract = next(c for name, c in _contracts().items() if name.startswith("ingestion is used"))
    assert contract["type"] == "forbidden"
    assert contract["forbidden_modules"] == ["interval_assistance.ingestion"]
    assert set(contract["source_modules"]) == {
        f"interval_assistance.{layer}" for layer in LOWER_LAYERS
    }


def test_contract_keeps_ingestion_independent_of_the_api() -> None:
    contract = next(c for name, c in _contracts().items() if name.startswith("ingestion does not"))
    assert contract["source_modules"] == ["interval_assistance.ingestion"]
    assert "interval_assistance.api" in contract["forbidden_modules"]


def test_the_original_four_contracts_are_still_present() -> None:
    names = " | ".join(_contracts())
    for fragment in ("core does not depend", "sensors are", "storage does not", "signal is pure"):
        assert fragment in names


def _imported_modules(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_no_lower_layer_source_imports_ingestion() -> None:
    offenders = [
        path.relative_to(ROOT).as_posix()
        for layer in LOWER_LAYERS
        for path in (SRC / layer).rglob("*.py")
        if any(m.startswith("interval_assistance.ingestion") for m in _imported_modules(path))
    ]
    assert offenders == []


def test_storage_repositories_stay_free_of_domain_and_api_imports() -> None:
    imported = _imported_modules(SRC / "storage" / "repositories.py")
    forbidden = ("sensors", "signal", "api", "ingestion")
    assert not [
        m for m in imported if any(m.startswith(f"interval_assistance.{f}") for f in forbidden)
    ]
