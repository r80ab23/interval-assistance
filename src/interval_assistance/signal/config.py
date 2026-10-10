"""Versioned signal-quality configuration (SCIENTIFIC_SPECIFICATION.md 5.1 and 5.1.1).

Every field is required and nothing has a default: this module chooses no threshold and no
state mapping. Identity is the SHA-256 of the canonical serialization of the hashed document.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

from interval_assistance.core.errors import ConfigurationError
from interval_assistance.signal.canonical import canonical_json
from interval_assistance.signal.reasons import SIGNAL_QUALITY_REASONS, QualityState, ReasonCode

FORMAT_TAG = "signal-quality-config/1"

_IDENTIFIER = re.compile(r"[A-Za-z0-9._-]{1,64}")
_NUMERIC_FIELDS = (
    "hr_min_bpm",
    "hr_max_bpm",
    "max_jump_bpm",
    "stale_after_seconds",
    "gap_after_seconds",
)
_REQUIRED_KEYS = frozenset(
    {"config_id", "config_version", "state_by_reason", "no_findings_state", *_NUMERIC_FIELDS}
)
_ALLOWED_KEYS = _REQUIRED_KEYS | {"format"}
_SIGNAL_QUALITY_CODES = {code.value: code for code in SIGNAL_QUALITY_REASONS}
_STATES = {state.value: state for state in QualityState}


def _number(name: str, value: object, problems: list[str]) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        problems.append(f"{name} must be a number (booleans and other types are rejected)")
        return math.nan
    try:
        result = float(value)  # ints above 2**53 round to nearest, ties to even
    except OverflowError:
        problems.append(f"{name} is not finite as binary64")
        return math.nan
    if not math.isfinite(result):
        problems.append(f"{name} must be finite")
        return math.nan
    return result


@dataclass(frozen=True, slots=True, eq=True)
class SignalQualityConfig:
    config_id: str
    config_version: str
    hr_min_bpm: float
    hr_max_bpm: float
    max_jump_bpm: float
    stale_after_seconds: float
    gap_after_seconds: float
    state_by_reason: Mapping[ReasonCode, QualityState]
    no_findings_state: QualityState

    def __post_init__(self) -> None:
        problems: list[str] = []
        for name in ("config_id", "config_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
                problems.append(f"{name} must match [A-Za-z0-9._-]{{1,64}}")
        numbers = {name: _number(name, getattr(self, name), problems) for name in _NUMERIC_FIELDS}
        if not problems and not numbers["hr_min_bpm"] < numbers["hr_max_bpm"]:
            problems.append("hr_min_bpm must be below hr_max_bpm")
        mapping = self.state_by_reason
        if (
            not isinstance(mapping, Mapping)
            or not all(isinstance(key, ReasonCode) for key in mapping)
            or set(mapping) != set(SIGNAL_QUALITY_REASONS)
        ):
            problems.append("state_by_reason must have exactly the five signal-quality codes")
        elif not all(isinstance(state, QualityState) for state in mapping.values()):
            problems.append("state_by_reason values must be quality states")
        if not isinstance(self.no_findings_state, QualityState):
            problems.append("no_findings_state must be a quality state")
        if problems:
            raise ConfigurationError(
                "invalid signal-quality configuration", details={"problems": problems}
            )
        for name, value in numbers.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "state_by_reason", MappingProxyType(dict(mapping)))

    def __hash__(self) -> int:
        return hash(self.config_hash())

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> SignalQualityConfig:
        """Build from untyped source data (for example parsed JSON), validating strictly.

        Missing and unknown keys are errors; `format` is optional but must equal the
        constant when present. Which file the data came from is not part of identity."""
        problems: list[str] = []
        if not isinstance(data, Mapping):
            raise ConfigurationError(
                "configuration must be an object", details={"problems": ["not an object"]}
            )
        keys = {key for key in data if isinstance(key, str)}
        if len(keys) != len(data):
            problems.append("all keys must be strings")
        for key in sorted(keys - _ALLOWED_KEYS):
            problems.append(f"unknown key: {key}")
        for key in sorted(_REQUIRED_KEYS - keys):
            problems.append(f"missing key: {key}")
        if "format" in data and data["format"] != FORMAT_TAG:
            problems.append(f"format must equal {FORMAT_TAG!r} when present")

        state_map: dict[ReasonCode, QualityState] = {}
        raw_map = data.get("state_by_reason")
        if "state_by_reason" in data:
            if not isinstance(raw_map, Mapping):
                problems.append("state_by_reason must be an object")
            else:
                for code, state in raw_map.items():
                    if not isinstance(code, str) or code not in _SIGNAL_QUALITY_CODES:
                        problems.append(f"state_by_reason has an invalid code: {code!r}")
                    elif not isinstance(state, str) or state not in _STATES:
                        problems.append(f"state_by_reason[{code}] must be a quality state name")
                    else:
                        state_map[_SIGNAL_QUALITY_CODES[code]] = _STATES[state]
                if set(raw_map) != set(_SIGNAL_QUALITY_CODES):
                    problems.append(
                        "state_by_reason must have exactly the five signal-quality codes"
                    )
        no_findings = data.get("no_findings_state")
        if "no_findings_state" in data and (
            not isinstance(no_findings, str) or no_findings not in _STATES
        ):
            problems.append("no_findings_state must be a quality state name")
        for key in ("config_id", "config_version"):
            if key in data and not isinstance(data[key], str):
                problems.append(f"{key} must be a string")
        if problems:
            raise ConfigurationError(
                "invalid signal-quality configuration", details={"problems": problems}
            )
        return cls(
            config_id=data["config_id"],
            config_version=data["config_version"],
            hr_min_bpm=data["hr_min_bpm"],
            hr_max_bpm=data["hr_max_bpm"],
            max_jump_bpm=data["max_jump_bpm"],
            stale_after_seconds=data["stale_after_seconds"],
            gap_after_seconds=data["gap_after_seconds"],
            state_by_reason=state_map,
            no_findings_state=_STATES[str(no_findings)],
        )

    def hashed_document(self) -> dict[str, object]:
        """The complete validated document that is hashed and stored as the run snapshot."""
        return {
            "format": FORMAT_TAG,
            "config_id": self.config_id,
            "config_version": self.config_version,
            "hr_min_bpm": self.hr_min_bpm,
            "hr_max_bpm": self.hr_max_bpm,
            "max_jump_bpm": self.max_jump_bpm,
            "stale_after_seconds": self.stale_after_seconds,
            "gap_after_seconds": self.gap_after_seconds,
            "state_by_reason": {
                code.value: state.value for code, state in self.state_by_reason.items()
            },
            "no_findings_state": self.no_findings_state.value,
        }

    def canonical_text(self) -> str:
        return canonical_json(self.hashed_document())

    def config_hash(self) -> str:
        """SHA-256 of the canonical text (UTF-8), as 64 lowercase hexadecimal characters."""
        return hashlib.sha256(self.canonical_text().encode("utf-8")).hexdigest()


def check_identity(config: SignalQualityConfig, known_hash: str | None) -> None:
    """A `(config_id, config_version)` pair is immutable: the same pair with a different hash
    is an error, the same hash is accepted. `known_hash` is the hash already recorded for the
    pair (None when the pair has not been seen); where it is stored is not this module's
    concern."""
    if known_hash is not None and known_hash != config.config_hash():
        raise ConfigurationError(
            "configuration identity conflict: the same id and version with different content",
            details={"config_id": config.config_id, "config_version": config.config_version},
        )
