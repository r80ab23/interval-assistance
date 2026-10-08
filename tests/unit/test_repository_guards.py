"""Repository and scope guards for the Phase 1 boundary (see docs/SPECIFICATION_REVIEW.md)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

ML_PACKAGES = {
    "torch",
    "tensorflow",
    "keras",
    "scikit-learn",
    "sklearn",
    "xgboost",
    "lightgbm",
    "catboost",
    "jax",
    "jaxlib",
    "transformers",
    "onnx",
    "onnxruntime",
    "mlflow",
    "statsmodels",
    "tensorflow-js",
    "@tensorflow/tfjs",
    "brain.js",
    "onnxruntime-web",
}
BLE_PACKAGES = {"bleak", "pybluez", "bluepy", "polar-ble-sdk", "web-bluetooth"}
FRONTEND_FORBIDDEN = {
    "redux",
    "@reduxjs/toolkit",
    "zustand",
    "mobx",
    "jotai",
    "recoil",
    "chart.js",
    "recharts",
    "d3",
    "victory",
    "plotly.js",
    "echarts",
    "uplot",
}
FORBIDDEN_SUFFIXES = {".xlsx", ".xls", ".fit", ".tcx", ".db", ".sqlite", ".sqlite3"}

# Scientific / hardware / later-phase terms that must not appear in Phase 1 source code.
FORBIDDEN_SOURCE_PATTERNS = {
    r"karvonen": "HRR/Karvonen formula",
    r"\bhrmax\b": "HRmax",
    r"\bhrr\b": "HRR",
    r"vo2": "VO2 functionality",
    r"polar": "Polar-specific code",
    r"\bbleak\b": "BLE transport",
    r"navigator\.bluetooth": "browser Bluetooth",
    r"sensor_?sample": "SensorSample persistence",
    r"\.websocket\(": "WebSocket endpoint",
    r"new WebSocket": "WebSocket client",
    r"import .*\bWebSocket\b": "WebSocket import",
    r"\b(torch|tensorflow|sklearn|keras|xgboost)\b": "ML library",
}


def _project_files() -> list[Path]:
    if shutil.which("git") is None:
        pytest.skip("git is not available")
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [ROOT / line for line in result.stdout.splitlines() if (ROOT / line).is_file()]


def _source_files() -> list[Path]:
    files = []
    for path in _project_files():
        rel = path.relative_to(ROOT).as_posix()
        in_scope = rel.startswith("src/") or rel.startswith("frontend/src/")
        is_test = "__tests__" in rel or rel.endswith((".test.ts", ".test.tsx"))
        if in_scope and not is_test and path.suffix in {".py", ".ts", ".tsx", ".css", ".html"}:
            files.append(path)
    return files


def test_no_ml_or_ble_python_dependencies() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    specs = list(project["dependencies"])
    for group in project.get("optional-dependencies", {}).values():
        specs.extend(group)
    names = {re.split(r"[<>=!~\[ ;]", spec, maxsplit=1)[0].lower() for spec in specs}
    assert not names & ML_PACKAGES
    assert not names & BLE_PACKAGES


def test_frontend_dependencies_are_within_phase_1() -> None:
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    names = set(package.get("dependencies", {})) | set(package.get("devDependencies", {}))
    assert not names & ML_PACKAGES
    assert not names & BLE_PACKAGES
    assert not names & FRONTEND_FORBIDDEN


def test_no_secrets_or_real_data_files() -> None:
    offenders = []
    for path in _project_files():
        rel = path.relative_to(ROOT).as_posix()
        is_env_file = path.name.startswith(".env") and path.name != ".env.example"
        is_data_file = path.suffix.lower() in FORBIDDEN_SUFFIXES
        is_unlabelled_data = rel.startswith("data/") and not rel.startswith("data/synthetic/")
        if is_env_file or is_data_file or is_unlabelled_data:
            offenders.append(rel)
    assert not offenders, offenders


@pytest.mark.parametrize(("pattern", "label"), list(FORBIDDEN_SOURCE_PATTERNS.items()))
def test_source_has_no_out_of_scope_content(pattern: str, label: str) -> None:
    regex = re.compile(pattern, re.IGNORECASE)
    hits = []
    for path in _source_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if regex.search(line):
                hits.append(f"{path.relative_to(ROOT).as_posix()}:{number}")
    assert not hits, f"{label}: {hits}"


def test_sensor_adapters_do_not_log() -> None:
    for path in (ROOT / "src" / "interval_assistance" / "sensors").glob("*.py"):
        assert "logging" not in path.read_text(encoding="utf-8"), path.name


def test_no_database_models_in_phase_1() -> None:
    from interval_assistance.storage.base import Base

    assert dict(Base.metadata.tables) == {}
    for path in (ROOT / "src").rglob("*.py"):
        assert "__tablename__" not in path.read_text(encoding="utf-8"), path.name
