"""Seeds expand through SeedSequence so streams never overlap (R-03)."""

from __future__ import annotations

import numpy as np


def rng(seed: int, *stream: int) -> np.random.Generator:
    """An independent generator for (seed, *stream)."""
    return np.random.default_rng(np.random.SeedSequence([seed, *stream]))
