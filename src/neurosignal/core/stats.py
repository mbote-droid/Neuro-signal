"""Interval estimates used by the validation report."""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

_Z95 = 1.959963984540054


def wilson(successes: int, n: int, z: float = _Z95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def rule_of_three(n: int) -> float:
    """95 % upper bound on a rate after zero events in n trials."""
    return 3.0 / n if n > 0 else 1.0


def poisson_upper(events: int, exposure: float, z: float = _Z95) -> float:
    """Approximate 95 % upper bound on a Poisson rate (Wilson-Hilferty)."""
    if exposure <= 0:
        return math.inf
    k = events + 1
    upper = k * (1 - 1 / (9 * k) + z / (3 * math.sqrt(k))) ** 3
    return upper / exposure


def benjamini_hochberg(p: NDArray[np.float64], q: float = 0.05) -> NDArray[np.bool_]:
    """Reject mask controlling the false discovery rate at q."""
    p = np.asarray(p, dtype=float)
    m = p.size
    order = np.argsort(p)
    thresholds = q * np.arange(1, m + 1) / m
    passed = p[order] <= thresholds
    reject = np.zeros(m, dtype=bool)
    if passed.any():
        k = int(np.max(np.nonzero(passed)[0]))
        reject[order[: k + 1]] = True
    return reject
