"""Canonical serialization for configuration hashing (SCIENTIFIC_SPECIFICATION.md 5.1.1).

Numbers follow the normative rule: digit selection as in ECMA-262 `Number::toString` (the
choice of integers n, k, s), computed here with exact rational arithmetic, then rendered in
plain positional notation. Nothing here depends on `repr`, `str` or a JSON library for
number formatting.
"""

from __future__ import annotations

import math
import re
import struct
from collections.abc import Mapping
from fractions import Fraction

_SAFE_STRING = re.compile(r"[A-Za-z0-9._/-]+")
_MAX_DIGITS = 17  # 17 significant digits always identify a binary64


def _mantissa_is_even(x: float) -> bool:
    bits: int = struct.unpack("<Q", struct.pack("<d", x))[0]
    return bits % 2 == 0


def _floor_log10(x: float, exact: Fraction) -> int:
    exponent = math.floor(math.log10(x))
    while Fraction(10) ** exponent > exact:
        exponent -= 1
    while Fraction(10) ** (exponent + 1) <= exact:
        exponent += 1
    return exponent


def select_digits(x: float) -> tuple[int, int, int]:
    """ECMA-262 Number::toString digit selection for a positive finite binary64 `x`.

    Returns (n, k, s) with 10**(k-1) <= s < 10**k, the binary64 nearest s * 10**(n-k)
    (round-to-nearest, ties-to-even) equal to `x`, and k minimal. Among several such s, the
    one closest in value to `x` wins; an exact tie goes to the even s. The set of decimals
    that round-trip is the rounding interval around `x`, which is asymmetric at powers of
    two; it is computed from the neighbouring doubles, never assumed symmetric.
    """
    if not (math.isfinite(x) and x > 0):
        raise ValueError("select_digits needs a positive finite number")
    exact = Fraction(x)
    below = Fraction(math.nextafter(x, 0.0))
    above = math.nextafter(x, math.inf)
    lower = (below + exact) / 2
    upper = exact + (exact - below) / 2 if math.isinf(above) else (exact + Fraction(above)) / 2
    boundaries_round_to_x = _mantissa_is_even(x)
    exponent = _floor_log10(x, exact)

    for k in range(1, _MAX_DIGITS + 1):
        best: tuple[tuple[Fraction, int], int, int] | None = None
        for n in (exponent + 1, exponent + 2):
            scale = Fraction(10) ** (n - k)
            for s in range(math.floor(lower / scale), math.ceil(upper / scale) + 1):
                if not 10 ** (k - 1) <= s < 10**k:
                    continue
                value = s * scale
                inside = lower < value < upper or (
                    boundaries_round_to_x and value in (lower, upper)
                )
                if not inside:
                    continue
                key = (abs(value - exact), s % 2)
                if best is None or key < best[0]:
                    best = (key, n, s)
        if best is not None:
            _, n, s = best
            if s % 10 == 0:  # unreachable: a shorter k would already have matched
                raise AssertionError("digit selection produced a trailing zero")
            return n, k, s
    raise AssertionError("no decimal representation found")  # pragma: no cover


def canonical_number(x: float) -> str:
    """Plain positional text of a finite binary64 (or an int, rounded to binary64)."""
    if isinstance(x, bool) or not isinstance(x, int | float):
        raise TypeError("canonical_number needs an int or float, not bool or other types")
    try:
        value = float(x)  # round-to-nearest, ties-to-even for ints above 2**53
    except OverflowError as error:
        raise ValueError("number is not finite as binary64") from error
    if not math.isfinite(value):
        raise ValueError("NaN and infinities are not serializable")
    if value == 0.0:
        return "0"
    n, k, s = select_digits(abs(value))
    digits = str(s)
    if len(digits) != k:  # pragma: no cover
        raise AssertionError("digit count mismatch")
    if n >= k:
        body = digits + "0" * (n - k)
    elif n > 0:
        body = digits[:n] + "." + digits[n:]
    else:
        body = "0." + "0" * (-n) + digits
    return "-" + body if value < 0 else body


def _string(text: str) -> str:
    if not _SAFE_STRING.fullmatch(text):
        raise ValueError("string is outside the canonical character set")
    return f'"{text}"'


def canonical_json(document: Mapping[str, object]) -> str:
    """Compact JSON, keys sorted by Unicode code point at every level, canonical numbers.

    Only objects, strings and numbers are supported (no arrays, booleans or null)."""
    return _render(document)


def _render(value: object) -> str:
    if isinstance(value, Mapping):
        items = sorted((str(key), item) for key, item in value.items())
        return "{" + ",".join(f"{_string(key)}:{_render(item)}" for key, item in items) + "}"
    if isinstance(value, str):
        return _string(value)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return canonical_number(value)
    raise TypeError(f"unsupported value in canonical document: {type(value).__name__}")
