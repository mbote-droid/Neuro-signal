"""Bug hunt: property-based fuzzing of the claim checker.

Two properties that must hold for any input:
1. `check` never raises, whatever text a model writes;
2. a number that differs from its cited metric beyond the written precision is
   never accepted, whatever form it is written in.
"""

from __future__ import annotations

from decimal import Decimal

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from neurosignal.explain.checker import check

METRICS = {"recording": {"channels": ["Fz", "Cz"]}, "x": {"v": 0.0}}
NOTICE = "research use only. "


@settings(max_examples=400, deadline=None)
@given(st.text(max_size=200), st.sampled_from(["x.v", "nope", "", " ", "x", "x.v.w", "0"]))
def test_check_never_raises(text, key):
    check(f"{NOTICE}{text} [[{key}]] {text}", METRICS)


@settings(max_examples=300, deadline=None)
@given(
    mantissa=st.integers(1, 999),
    exponent=st.integers(-400, 400),
    sign=st.sampled_from(["", "-", "+", "−"]),
)
def test_exponents_of_any_size_do_not_crash(mantissa, exponent, sign):
    check(f"{NOTICE}{sign}{mantissa}e{exponent} [[x.v]]", METRICS)


def _render(value: float, decimals: int, form: str) -> str:
    text = f"{abs(value):.{decimals}f}"
    sign = "-" if value < 0 else ""
    if form == "unicode_minus":
        sign = "−" if value < 0 else ""
    if form == "exponent":
        text = f"{abs(value):.{decimals}e}"
    if form == "leading_dot" and text.startswith("0."):
        text = text[1:]
    return sign + text


@settings(max_examples=500, deadline=None)
@given(
    value=st.floats(-1e6, 1e6, allow_nan=False).map(lambda v: round(v, 4)),
    decimals=st.integers(0, 4),
    units_off=st.integers(1, 1000),
    direction=st.sampled_from([-1, 1]),
    form=st.sampled_from(["plain", "unicode_minus", "exponent", "leading_dot"]),
)
def test_a_wrong_value_is_never_accepted(value, decimals, units_off, direction, form):
    wrong = value + direction * units_off * 10.0**-decimals
    written = _render(wrong, decimals, form)
    # the written precision, from Decimal (independent of the checker's parser):
    # "1e+01" is 10 +/- 5, so only differences beyond half a unit are wrong
    exact = Decimal(written.replace("\u2212", "-"))
    half = Decimal(5).scaleb(exact.as_tuple().exponent - 1)
    assume(abs(exact - Decimal(repr(value))) > half * Decimal("1.000001"))
    metrics = {"recording": {"channels": []}, "x": {"v": value}}
    result = check(f"{NOTICE}It was {written} [[x.v]].", metrics)
    assert not result.ok, (written, value)


@settings(max_examples=300, deadline=None)
@given(
    value=st.floats(-1e6, 1e6, allow_nan=False).map(lambda v: round(v, 4)),
    junk=st.sampled_from(["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff", "\u00ad"]),
    split=st.integers(0, 6),
)
def test_invisible_characters_cannot_hide_a_digit(value, junk, split):
    """A zero-width character inside a number would show '1.5' while the checker
    reads '1'; text containing such characters must not pass."""
    shown = f"{value:.3f}"
    i = min(split, len(shown))
    written = shown[:i] + junk + shown[i:]
    metrics = {"recording": {"channels": []}, "x": {"v": value}}
    assert not check(f"{NOTICE}It was {written} [[x.v]].", metrics).ok


@settings(max_examples=200, deadline=None)
@given(digits=st.integers(1, 99), decimals=st.integers(1, 3))
def test_an_uncited_number_is_never_invisible(digits, decimals):
    """Every way of writing a number must be seen, including a leading decimal
    point ('.5', common in American writing)."""
    for written in (f"{digits}", f"{digits}.{'5' * decimals}", f".{'5' * decimals}"):
        result = check(f"{NOTICE}There were {written} spikes.", METRICS)
        assert "UNCITED_NUMBER" in result.codes(), written
