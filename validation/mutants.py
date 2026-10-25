"""Mutation operators for explanations (H4): realistic ways an LLM summary
goes wrong. Each takes a faithful text and returns a mutated text, or None
when the operator does not apply. A mutant whose claims are still true at
the precision written is *equivalent* and is counted separately.

`number_as_words` is outside the citation contract (the checker only sees
digits) and is reported as a known blind spot, not counted towards H4.
"""

from __future__ import annotations

import random
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from neurosignal.explain.checker import CITATION, NUMBER
from neurosignal.pipeline import flatten


@dataclass(frozen=True)
class Mutant:
    text: str
    equivalent: bool = False  # decided from metric values, never by the checker


Mutator = Callable[[str, dict[str, Any], random.Random], Mutant | None]


# Dashes a model may write as a minus sign; listed here, not imported from the
# checker, so the equivalence oracle stays independent of the code it tests.
_ASCII_SIGN = str.maketrans(dict.fromkeys("\u2010\u2011\u2012\u2013\u2212\ufe63\uff0d", "-"))


def true_at_precision(written: str, value: float) -> bool:
    """Independent of the checker's code: is `written` within (strictly) half a
    unit of its last decimal place from the metric value? Integer arithmetic on
    scaled values avoids sharing the checker's floating-point path."""
    written = written.translate(_ASCII_SIGN)
    d = len(written.split(".")[1]) if "." in written else 0
    scale = 10**d
    w_units = int(written.replace(".", "").replace("-", "")) * (
        -1 if written.startswith("-") else 1
    )
    return abs(w_units - value * scale) * 2 < 1 - 1e-9


FAKE_CHANNELS = ("T9", "Fp3", "O5", "FT11", "P11")
DIAGNOSTIC_SENTENCES = (
    "These findings are consistent with epilepsy.",
    "The EEG is abnormal.",
    "This pattern suggests a seizure disorder.",
    "Overall this is a normal EEG.",
    "The slowing indicates encephalopathy.",
)


def _cited_numbers(text: str) -> list[tuple[re.Match[str], re.Match[str]]]:
    """(number, citation) pairs where the number is the last one before the citation."""
    pairs = []
    prev = 0
    for c in CITATION.finditer(text):
        nums = list(NUMBER.finditer(text, prev, c.start()))
        if nums:
            pairs.append((nums[-1], c))
        prev = c.end()
    return pairs


def _fmt_like(written: str, value: float) -> str:
    d = len(written.split(".")[1]) if "." in written else 0
    return f"{value:.{d}f}"


def perturb_number(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    pairs = _cited_numbers(text)
    if not pairs:
        return None
    num, cite = rng.choice(pairs)
    w = num.group()
    d = len(w.split(".")[1]) if "." in w else 0
    step = max(abs(float(w)) * rng.choice((0.05, 0.1, 0.25, 0.5)), 10.0**-d * rng.randint(1, 5))
    new = _fmt_like(w, float(w) + rng.choice((-1, 1)) * step)
    value = flatten(metrics)[cite.group(1)]
    return Mutant(text[: num.start()] + new + text[num.end() :], true_at_precision(new, value))


def scale_1000(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    """A unit slip (µV written as mV or the reverse)."""
    pairs = [(n, c) for n, c in _cited_numbers(text) if float(n.group()) != 0]
    if not pairs:
        return None
    num, cite = rng.choice(pairs)
    factor = rng.choice((1000.0, 0.001))
    new = _fmt_like(num.group(), float(num.group()) * factor)
    if new == num.group():
        new = f"{float(num.group()) * factor:g}"
    value = flatten(metrics)[cite.group(1)]
    return Mutant(text[: num.start()] + new + text[num.end() :], true_at_precision(new, value))


def swap_key(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    flat = flatten(metrics)
    numeric = [k for k, v in flat.items() if isinstance(v, int | float) and not isinstance(v, bool)]
    pairs = _cited_numbers(text)
    if not pairs or len(numeric) < 2:
        return None
    num, cite = rng.choice(pairs)
    other = rng.choice([k for k in numeric if k != cite.group(1)])
    equivalent = true_at_precision(num.group(), float(flat[other]))
    return Mutant(text[: cite.start()] + f"[[{other}]]" + text[cite.end() :], equivalent)


def unknown_key(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    cites = list(CITATION.finditer(text))
    if not cites:
        return None
    c = rng.choice(cites)
    bogus = rng.choice((c.group(1) + "_median", "aperiodic.knee.mean", "spectral.theta_power"))
    return Mutant(text[: c.start()] + f"[[{bogus}]]" + text[c.end() :])


def uncited_number(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    sentence = rng.choice(
        (
            f"About {rng.randint(2, 90)} artifacts were removed.",
            f"The posterior dominant rhythm was {rng.uniform(7, 12):.1f} Hz.",
            f"Signal quality was {rng.randint(60, 99)}% good.",
        )
    )
    paras = text.split("\n\n")
    i = rng.randrange(1, len(paras)) if len(paras) > 1 else 0
    paras[i] = paras[i] + " " + sentence
    return Mutant("\n\n".join(paras))


def drop_citation(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    pairs = _cited_numbers(text)
    if not pairs:
        return None
    _, cite = rng.choice(pairs)
    return Mutant(text[: cite.start()] + text[cite.end() :])


def diagnostic(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    return Mutant(text.rstrip() + " " + rng.choice(DIAGNOSTIC_SENTENCES) + "\n")


def no_disclaimer(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    out = re.sub(r"research use only\.?", "", text, flags=re.IGNORECASE)
    return Mutant(out) if out != text else None


def fake_channel(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    channels = sorted(metrics["recording"]["channels"], key=len, reverse=True)
    stripped = CITATION.sub(lambda m: " " * len(m.group()), text)
    for ch in channels:
        m = re.search(rf"(?<![\w\-]){re.escape(ch)}(?![\w\-])", stripped)
        if m:
            fake = rng.choice(
                [c for c in FAKE_CHANNELS if c.lower() not in map(str.lower, channels)]
            )
            return Mutant(text[: m.start()] + fake + text[m.end() :])
    return None


def typographic_minus(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    """A sign flip written with a typographic minus or en dash (issue #21)."""
    pairs = [
        (n, c) for n, c in _cited_numbers(text)
        if n.group()[0].isdigit() and (n.start() == 0 or text[n.start() - 1] in " (")
    ]  # fmt: skip
    if not pairs:
        return None
    num, cite = rng.choice(pairs)
    dash = rng.choice(("\u2212", "\u2013"))
    value = flatten(metrics)[cite.group(1)]
    equivalent = true_at_precision("-" + num.group(), float(value))  # e.g. 0.000
    return Mutant(text[: num.start()] + dash + text[num.start() :], equivalent)


def swap_citations(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    """Two numbers trade citations, e.g. 'before' and 'after' swapped (bug hunt)."""
    flat = flatten(metrics)
    pairs = [(n, c) for n, c in _cited_numbers(text) if _is_number(flat.get(c.group(1)))]
    if len(pairs) < 2:
        return None
    (n1, c1), (n2, c2) = sorted(rng.sample(pairs, 2), key=lambda p: p[1].start())
    k1, k2 = c1.group(1), c2.group(1)
    if k1 == k2:
        return None
    out = text[: c1.start()] + f"[[{k2}]]" + text[c1.end() : c2.start()] + f"[[{k1}]]"
    out += text[c2.end() :]
    equivalent = true_at_precision(n1.group(), float(flat[k2])) and true_at_precision(
        n2.group(), float(flat[k1])
    )
    return Mutant(out, equivalent)


def markup_sign_flip(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    """A sign flip inside bold markup, as models write numbers: '**-1.23**'."""
    pairs = [(n, c) for n, c in _cited_numbers(text) if n.group()[0].isdigit()]
    if not pairs:
        return None
    num, cite = rng.choice(pairs)
    value = float(flatten(metrics)[cite.group(1)])
    new = f"**-{num.group()}**"
    return Mutant(text[: num.start()] + new + text[num.end() :],
                  true_at_precision("-" + num.group(), value))  # fmt: skip


def zero_width_decimal(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    """An integer gains a decimal behind a zero-width joiner: '1<ZWJ>.5' shows 1.5."""
    pairs = [(n, c) for n, c in _cited_numbers(text) if n.group().isdigit()]
    if not pairs:
        return None
    num, cite = rng.choice(pairs)
    digit = rng.randint(1, 9)
    value = float(flatten(metrics)[cite.group(1)])
    shown = f"{num.group()}.{digit}"
    return Mutant(text[: num.end()] + f"\u200d.{digit}" + text[num.end() :],
                  true_at_precision(shown, value))  # fmt: skip


def uncited_leading_dot(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    """An uncited number written with a leading decimal point ('.8')."""
    sentence = rng.choice(
        ("Roughly .8 of the epochs were clean.", "About .25 of channels drifted.")
    )
    paras = text.split("\n\n")
    i = rng.randrange(1, len(paras)) if len(paras) > 1 else 0
    paras[i] = paras[i] + " " + sentence
    return Mutant("\n\n".join(paras))


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def number_as_words(text: str, metrics: dict[str, Any], rng: random.Random) -> Mutant | None:
    """Out of contract: a wrong count written in words is invisible to the checker."""
    return Mutant(text.rstrip() + " Seven channels showed clear slowing.\n")


OPERATORS: dict[str, Mutator] = {
    "perturb_number": perturb_number,
    "scale_1000": scale_1000,
    "swap_key": swap_key,
    "unknown_key": unknown_key,
    "uncited_number": uncited_number,
    "drop_citation": drop_citation,
    "diagnostic": diagnostic,
    "no_disclaimer": no_disclaimer,
    "fake_channel": fake_channel,
    "typographic_minus": typographic_minus,
    "swap_citations": swap_citations,
    "markup_sign_flip": markup_sign_flip,
    "zero_width_decimal": zero_width_decimal,
    "uncited_leading_dot": uncited_leading_dot,
}
BLIND_SPOTS: dict[str, Mutator] = {"number_as_words": number_as_words}
