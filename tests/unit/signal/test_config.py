from __future__ import annotations

import copy
import dataclasses
import math
from typing import Any

import pytest

from interval_assistance.core.errors import ConfigurationError
from interval_assistance.signal import (
    FORMAT_TAG,
    QualityState,
    ReasonCode,
    SignalQualityConfig,
    check_identity,
)

from .helpers import (
    DOC_CANONICAL_TEXT,
    DOC_CONFIG_SHA256,
    DOC_CONFIG_SOURCE,
    make_config,
    make_state_map,
)


def source(**changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(DOC_CONFIG_SOURCE)
    data.update(changes)
    return data


def test_documented_test_vector_text_and_hash() -> None:
    config = make_config()
    assert config.canonical_text() == DOC_CANONICAL_TEXT
    assert len(DOC_CANONICAL_TEXT.encode()) == 354
    assert config.config_hash() == DOC_CONFIG_SHA256


def test_hashed_document_has_the_format_tag_and_exactly_ten_keys() -> None:
    document = make_config().hashed_document()
    assert document["format"] == FORMAT_TAG == "signal-quality-config/1"
    assert set(document) == {
        "format",
        "config_id",
        "config_version",
        "hr_min_bpm",
        "hr_max_bpm",
        "max_jump_bpm",
        "stale_after_seconds",
        "gap_after_seconds",
        "state_by_reason",
        "no_findings_state",
    }
    assert set(document["state_by_reason"]) == {  # type: ignore[call-overload]
        "duplicate_timestamp",
        "out_of_order_timestamp",
        "implausible_jump",
        "gap",
        "stale",
    }


def test_hash_is_64_lowercase_hex() -> None:
    value = make_config().config_hash()
    assert len(value) == 64 and value == value.lower() and set(value) <= set("0123456789abcdef")


def test_source_key_order_does_not_change_the_hash() -> None:
    reordered = dict(reversed(list(source().items())))
    assert SignalQualityConfig.from_mapping(reordered).config_hash() == DOC_CONFIG_SHA256


def test_integer_and_float_spellings_share_one_hash() -> None:
    assert make_config(hr_min_bpm=10.0, gap_after_seconds=7.0).config_hash() == DOC_CONFIG_SHA256


def test_format_key_is_optional_but_must_equal_the_constant() -> None:
    assert make_config(format=FORMAT_TAG).config_hash() == DOC_CONFIG_SHA256
    with pytest.raises(ConfigurationError):
        make_config(format="signal-quality-config/2")


@pytest.mark.parametrize(
    "key",
    [
        "config_id",
        "config_version",
        "hr_min_bpm",
        "hr_max_bpm",
        "max_jump_bpm",
        "stale_after_seconds",
        "gap_after_seconds",
        "state_by_reason",
        "no_findings_state",
    ],
)
def test_every_field_is_required_with_no_default(key: str) -> None:
    data = source()
    del data[key]
    with pytest.raises(ConfigurationError) as caught:
        SignalQualityConfig.from_mapping(data)
    assert f"missing key: {key}" in caught.value.details["problems"]


def test_unknown_keys_are_an_error() -> None:
    with pytest.raises(ConfigurationError) as caught:
        make_config(surprise=1)
    assert "unknown key: surprise" in caught.value.details["problems"]


def test_direct_construction_has_no_defaults_either() -> None:
    with pytest.raises(TypeError):
        SignalQualityConfig()  # type: ignore[call-arg]


@pytest.mark.parametrize("field", ["hr_min_bpm", "hr_max_bpm", "max_jump_bpm"])
@pytest.mark.parametrize("bad", [True, False, "5", None, [5], {}])
def test_non_numbers_and_booleans_are_rejected(field: str, bad: object) -> None:
    with pytest.raises(ConfigurationError):
        make_config(**{field: bad})


@pytest.mark.parametrize(
    "field",
    ["hr_min_bpm", "hr_max_bpm", "max_jump_bpm", "stale_after_seconds", "gap_after_seconds"],
)
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, 10**400])
def test_non_finite_numbers_are_rejected(field: str, bad: float) -> None:
    with pytest.raises(ConfigurationError):
        make_config(**{field: bad})


def test_hr_bounds_must_be_ordered() -> None:
    for low, high in ((20, 20), (21, 20)):
        with pytest.raises(ConfigurationError):
            make_config(hr_min_bpm=low, hr_max_bpm=high)


@pytest.mark.parametrize("good", ["a", "A.b_c-9", "x" * 64])
def test_identifier_pattern_accepts(good: str) -> None:
    assert make_config(config_id=good, config_version=good).config_id == good


@pytest.mark.parametrize("bad", ["", "x" * 65, "a b", "a/b", "café", "a\n", "\na", "a\x00"])
def test_identifier_pattern_rejects(bad: str) -> None:
    with pytest.raises(ConfigurationError):
        make_config(config_id=bad)
    with pytest.raises(ConfigurationError):
        make_config(config_version=bad)


def test_identifiers_must_be_strings() -> None:
    with pytest.raises(ConfigurationError):
        make_config(config_id=1)


def test_state_by_reason_needs_exactly_the_five_codes() -> None:
    base = dict(DOC_CONFIG_SOURCE["state_by_reason"])
    missing = {k: v for k, v in base.items() if k != "gap"}
    extra = {**base, "malformed_sample": "INVALID"}
    candidates: list[object] = [
        missing,
        extra,
        {},
        [],
        "POOR",
        {**base, "gap": "BAD"},
        {**base, "gap": 1},
    ]
    for bad in candidates:
        with pytest.raises(ConfigurationError):
            make_config(state_by_reason=bad)


def test_no_findings_state_must_be_a_state_name() -> None:
    for bad in ("good", "FINE", 1, None):
        with pytest.raises(ConfigurationError):
            make_config(no_findings_state=bad)


@pytest.mark.parametrize("state", list(QualityState))
def test_every_state_is_accepted_as_no_findings_state(state: QualityState) -> None:
    assert make_config(no_findings_state=state.value).no_findings_state is state


def test_not_an_object_is_an_error() -> None:
    with pytest.raises(ConfigurationError):
        SignalQualityConfig.from_mapping([])  # type: ignore[arg-type]


def test_configuration_is_immutable() -> None:
    config = make_config()
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.hr_min_bpm = 1.0  # type: ignore[misc]
    with pytest.raises(TypeError):
        config.state_by_reason[ReasonCode.GAP] = QualityState.GOOD  # type: ignore[index]
    source_map = make_state_map()
    built = SignalQualityConfig(
        config_id="c",
        config_version="1",
        hr_min_bpm=1,
        hr_max_bpm=2,
        max_jump_bpm=1,
        stale_after_seconds=1,
        gap_after_seconds=1,
        state_by_reason=source_map,
        no_findings_state=QualityState.GOOD,
    )
    source_map[ReasonCode.GAP] = QualityState.GOOD  # later mutation of the caller's dict
    assert built.state_by_reason[ReasonCode.GAP] is QualityState.MISSING


def test_equal_configurations_are_equal_and_hashable() -> None:
    assert make_config() == make_config()
    assert hash(make_config()) == hash(make_config())
    assert make_config() != make_config(max_jump_bpm=6)


def test_any_value_change_changes_the_hash() -> None:
    base = make_config().config_hash()
    for change in (
        {"config_version": "2"},
        {"hr_min_bpm": 11},
        {"hr_max_bpm": 21},
        {"max_jump_bpm": 5.5},
        {"stale_after_seconds": 3.25},
        {"gap_after_seconds": 8},
        {"no_findings_state": "ACCEPTABLE"},
        {"state_by_reason": {**DOC_CONFIG_SOURCE["state_by_reason"], "gap": "POOR"}},
    ):
        assert make_config(**change).config_hash() != base, change


def test_identity_pair_is_immutable() -> None:
    config = make_config()
    check_identity(config, None)  # pair not seen yet
    check_identity(config, config.config_hash())  # same content: idempotent
    changed = make_config(max_jump_bpm=6)  # same id and version, different content
    with pytest.raises(ConfigurationError) as caught:
        check_identity(changed, config.config_hash())
    assert caught.value.details == {"config_id": "example-test-config", "config_version": "1"}
    # A new version is a new identity: no hash is recorded for it yet, so nothing conflicts.
    check_identity(make_config(config_version="2", max_jump_bpm=6), None)
