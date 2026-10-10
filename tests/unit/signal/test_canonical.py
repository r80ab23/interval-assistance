from __future__ import annotations

import hashlib
import math
from decimal import Decimal

import pytest

from interval_assistance.signal import canonical_json, canonical_number
from interval_assistance.signal.canonical import select_digits


def informative_recipe(x: float) -> str:
    """The informative Python recipe, used here only as an independent oracle."""
    if x == 0:
        return "0"
    text = format(Decimal(repr(float(x))), "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


DOCUMENTED_VECTORS: list[tuple[float, str]] = [
    (100, "100"),
    (100.0, "100"),
    (0.1, "0.1"),
    (1.5, "1.5"),
    (-0.0, "0"),
    (-3.0, "-3"),
    (1e-7, "0.0000001"),
    (2.5e-5, "0.000025"),
    (1e21, "1000000000000000000000"),
    (123456789.125, "123456789.125"),
    (1e22, "10000000000000000000000"),
    (1e23, "100000000000000000000000"),
]


@pytest.mark.parametrize(("value", "expected"), DOCUMENTED_VECTORS)
def test_documented_number_vectors(value: float, expected: str) -> None:
    assert canonical_number(value) == expected


def test_positive_and_negative_zero_render_as_zero() -> None:
    assert canonical_number(0.0) == canonical_number(-0.0) == canonical_number(0) == "0"


def test_integral_floats_and_ints_share_one_text() -> None:
    assert canonical_number(100) == canonical_number(100.0) == "100"


def test_smallest_subnormal_vector() -> None:
    text = canonical_number(5e-324)
    assert text == "0." + "0" * 323 + "5" and len(text) == 326
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "90620a380b105dc799edca0bcb5c167ec1a00ff0fd1cd5f577593725fafb476d"
    )
    assert select_digits(5e-324) == (-323, 1, 5)


def test_largest_finite_vector() -> None:
    text = canonical_number(1.7976931348623157e308)
    assert text == "17976931348623157" + "0" * 292 and len(text) == 309
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "9a8a48349f1f23a94cc13b2f7dd1a5cb791c6cb8912f77cb425eca0f4f9b5a73"
    )
    assert select_digits(1.7976931348623157e308) == (309, 17, 17976931348623157)


def test_power_of_two_asymmetry_vector() -> None:
    x = 2.0**-1017
    text = canonical_number(x)
    assert text == "0." + "0" * 306 + "7120236347223045" and len(text) == 324
    assert (
        hashlib.sha256(text.encode()).hexdigest()
        == "ed157d6d5c5a705a0c030f0d7d47d6ab7ccf44fc34131e06d158e6794a43889a"
    )
    # The informal "nearest k-digit decimal that round-trips" method would need 17 digits here.
    assert select_digits(x) == (-306, 16, 7120236347223045)


def test_halfway_boundary_case_1e23() -> None:
    # 10**23 is exactly midway between two adjacent doubles; the literal rounds to the even one.
    assert select_digits(1e23) == (24, 1, 1)


def test_all_positive_powers_of_two_match_the_independent_oracle() -> None:
    for exponent in range(-1074, 1024):
        x = 2.0**exponent
        assert canonical_number(x) == informative_recipe(x), exponent
        assert float(canonical_number(x)) == x, exponent


def test_integers_above_2_pow_53_round_to_nearest_even_binary64() -> None:
    assert canonical_number(2**53 + 1) == canonical_number(float(2**53 + 1)) == str(2**53)
    assert canonical_number(2**53 + 3) == str(2**53 + 4)


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf, 10**400, -(10**400)])
def test_non_finite_numbers_are_rejected(bad: float) -> None:
    with pytest.raises(ValueError):
        canonical_number(bad)


@pytest.mark.parametrize("bad", [True, False, "1", None, [1]])
def test_non_numbers_are_rejected(bad: object) -> None:
    with pytest.raises(TypeError):
        canonical_number(bad)  # type: ignore[arg-type]


def test_canonical_json_sorts_keys_at_every_level_and_is_compact() -> None:
    document = {"b": 1, "a": {"z": 2.5, "m": "x"}, "C": 0}
    assert canonical_json(document) == '{"C":0,"a":{"m":"x","z":2.5},"b":1}'


def test_canonical_json_rejects_unsupported_values_and_unsafe_strings() -> None:
    for bad in ({"a": True}, {"a": None}, {"a": [1]}, {"a": "has space"}, {"a": 'q"'}, {"a b": 1}):
        with pytest.raises((TypeError, ValueError)):
            canonical_json(bad)
    with pytest.raises(ValueError):
        canonical_json({"a": math.nan})
