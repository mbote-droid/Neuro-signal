"""Mechanical claim checker for explanations (F-16, ADR-009, EQUATIONS §8).

Contract: every number in an explanation is written immediately before a
citation `[[dotted.metric.key]]`, e.g. "exponent 1.23 [[aperiodic.exponent.mean]]".
The checker uses no model. It reports one finding per violation:

  UNKNOWN_KEY        the cited key is not in the metrics
  VALUE_MISMATCH     the number before a citation differs from the metric at
                     the precision written (|w - v| not below half a unit in
                     the last written decimal place)
  MISSING_VALUE      a citation has no number (numeric metric) or does not
                     contain the cited text (string / list metric) before it
  UNCITED_NUMBER     a number with no citation
  UNKNOWN_CHANNEL    an electrode-like token not in the recording
  DIAGNOSTIC         diagnostic language (the tool is research use only)
  NO_DISCLAIMER      the research-use-only notice is missing
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from neurosignal.pipeline import flatten

CITATION = re.compile(r"\[\[([^\[\]]+)\]\]")
# A number is any digit run not glued to a preceding letter (so "T7", "log10"
# and "FT10" are not numbers, but "8-12", "30s" and "10Hz" expose every number).
NUMBER = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")
_ELECTRODE = r"(?:[A-Z][A-Za-z]{0,3}\d{1,2}|[A-Z][A-Za-z]{0,2}[zZ])"
CHANNEL = re.compile(rf"(?<![\w\-]){_ELECTRODE}(?:-{_ELECTRODE})?(?![\w\-])")
NOT_CHANNELS = frozenset({"Hz", "kHz", "MHz"})
DIAGNOSTIC = re.compile(
    r"\b(epilep\w*|diagnos\w*|patholog\w*|abnormal\w*|normal\s+EEG|lesions?|tumou?rs?|"
    r"encephalopath\w*|ictal|interictal|status\s+epilepticus|seizures?(?!-like)|"
    r"disorders?|diseases?)\b",
    re.IGNORECASE,
)
DISCLAIMER = re.compile(r"research use only", re.IGNORECASE)


@dataclass(frozen=True)
class Finding:
    code: str
    detail: str


@dataclass(frozen=True)
class CheckResult:
    findings: tuple[Finding, ...]
    n_citations: int
    n_numbers: int

    @property
    def ok(self) -> bool:
        return not self.findings

    def codes(self) -> set[str]:
        return {f.code for f in self.findings}


def _matches(written: str, value: float) -> bool:
    """Strictly less than half a unit in the last written place. An exact tie
    (0.5 written as 0 or 1) is ambiguous between rounding conventions and is
    rejected: write one more decimal (BUILD_JOURNAL ISSUE-007)."""
    decimals = len(written.split(".")[1]) if "." in written else 0
    half = 0.5 * 10.0**-decimals
    return abs(float(written) - value) < half - 1e-12 * max(1.0, abs(value))


def _numeric(key: str, segment: str, value: float) -> tuple[Finding | None, bool]:
    numbers = list(NUMBER.finditer(segment))
    if not numbers:
        return Finding("MISSING_VALUE", f"{key}: no number before citation"), False
    written = numbers[-1].group()
    if _matches(written, float(value)):
        return None, True
    return Finding("VALUE_MISMATCH", f"{key}: wrote {written}, metric is {value}"), True


def _textual(key: str, segment: str, value: Any) -> Finding | None:
    if isinstance(value, list):
        if not value:
            said_none = re.search(r"\b(none|no)\b", segment, re.IGNORECASE)
            return None if said_none else Finding("MISSING_VALUE", f"{key}: empty, not stated")
        missing = [str(v) for v in value if str(v).lower() not in segment.lower()]
        return Finding("MISSING_VALUE", f"{key}: {missing} not stated") if missing else None
    if str(value).lower() in segment.lower():
        return None
    return Finding("MISSING_VALUE", f"{key}: {value!r} not stated")


def _check_citation(key: str, segment: str, value: Any) -> tuple[Finding | None, bool]:
    """Returns (finding, whether the segment's last number was used by this citation)."""
    if value is None:
        return None, False
    if isinstance(value, int | float) and not isinstance(value, bool):
        return _numeric(key, segment, value)
    if isinstance(value, bool | str | list):
        return _textual(key, segment, value), False
    return Finding("MISSING_VALUE", f"{key}: cannot cite a {type(value).__name__}"), False


def _citations(text: str, flat: dict[str, Any]) -> tuple[list[Finding], set[int], int]:
    """Check every citation; return findings, offsets of numbers used, and the count."""
    findings: list[Finding] = []
    consumed: set[int] = set()
    prev_end = 0
    cites = list(CITATION.finditer(text))
    for m in cites:
        key = m.group(1).strip()
        start = prev_end
        segment = text[start : m.start()]
        prev_end = m.end()
        numbers = list(NUMBER.finditer(segment))
        if key not in flat:
            findings.append(Finding("UNKNOWN_KEY", key))
            used = bool(numbers)  # the number is attributed, wrongly; don't double-report
        else:
            finding, used = _check_citation(key, segment, flat[key])
            if finding:
                findings.append(finding)
        if used and numbers:
            consumed.add(start + numbers[-1].start())
    return findings, consumed, len(cites)


def _lexical(stripped: str, channels: set[str]) -> list[Finding]:
    findings = [
        Finding("UNKNOWN_CHANNEL", c.group())
        for c in CHANNEL.finditer(stripped)
        if c.group() not in NOT_CHANNELS and c.group().lower() not in channels
    ]
    findings += [Finding("DIAGNOSTIC", d.group()) for d in DIAGNOSTIC.finditer(stripped)]
    return findings


def check(text: str, metrics: dict[str, Any]) -> CheckResult:
    flat = flatten(metrics)
    channels = {c.lower() for c in metrics.get("recording", {}).get("channels", [])}
    findings, consumed, n_cites = _citations(text, flat)
    stripped = CITATION.sub(lambda mm: " " * len(mm.group()), text)
    numbers = list(NUMBER.finditer(stripped))
    for n in numbers:
        if n.start() not in consumed:
            context = stripped[max(0, n.start() - 30) : n.end() + 10].strip()
            findings.append(Finding("UNCITED_NUMBER", f"{n.group()} in '...{context}...'"))
    findings += _lexical(stripped, channels)
    if not DISCLAIMER.search(text):
        findings.append(Finding("NO_DISCLAIMER", "missing 'research use only'"))
    return CheckResult(tuple(findings), n_citations=n_cites, n_numbers=len(numbers))
