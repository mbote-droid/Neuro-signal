"""The one data model passed between stages.

A `Recording` is frozen: stages return a new recording instead of mutating
the input, so raw data stay read-only (ARCHITECTURE §2) and every stage's
parameters are appended to `history` (ADR-001).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

_BIPOLAR = re.compile(r"^[A-Za-z0-9']+-[A-Za-z0-9']+$")


@dataclass(frozen=True)
class Annotation:
    """An event marked in the recording; times in seconds from the start."""

    onset_s: float
    duration_s: float
    description: str


@dataclass(frozen=True)
class Recording:
    """Multichannel EEG.

    data: (n_channels, n_samples) float64, microvolts.
    sfreq: sampling rate in Hz.
    """

    data: FloatArray
    sfreq: float
    channels: tuple[str, ...]
    annotations: tuple[Annotation, ...] = ()
    bad_channels: tuple[str, ...] = ()
    source_sha256: str = ""
    subject_id: str = "anonymous"
    history: tuple[dict[str, Any], ...] = field(default=())

    def __post_init__(self) -> None:
        if self.data.ndim != 2:
            raise ValueError(f"data must be 2-D (channels, samples), got shape {self.data.shape}")
        if self.data.shape[0] != len(self.channels):
            raise ValueError(
                f"{self.data.shape[0]} rows of data but {len(self.channels)} channel names"
            )
        if len(set(self.channels)) != len(self.channels):
            raise ValueError("channel names must be unique")
        if not np.isfinite(self.sfreq) or self.sfreq <= 0:
            raise ValueError(f"sampling rate must be positive, got {self.sfreq}")
        if self.data.dtype != np.float64:
            raise TypeError(f"data must be float64 microvolts, got {self.data.dtype}")
        unknown = set(self.bad_channels) - set(self.channels)
        if unknown:
            raise ValueError(f"bad channels not in recording: {sorted(unknown)}")
        self.data.setflags(write=False)

    @property
    def n_channels(self) -> int:
        return int(self.data.shape[0])

    @property
    def n_samples(self) -> int:
        return int(self.data.shape[1])

    @property
    def duration_s(self) -> float:
        return self.n_samples / self.sfreq

    @property
    def good_channels(self) -> tuple[str, ...]:
        return tuple(c for c in self.channels if c not in self.bad_channels)

    @property
    def is_bipolar(self) -> bool:
        """True when every channel name looks like a derivation `A-B`."""
        return all(_BIPOLAR.match(c) for c in self.channels)

    def index(self, names: tuple[str, ...] | list[str]) -> list[int]:
        return [self.channels.index(n) for n in names]

    def evolve(self, step: dict[str, Any] | None = None, **changes: Any) -> Recording:
        """A copy with `changes` applied and `step` appended to the history."""
        history = self.history + ((step,) if step is not None else ())
        return replace(self, history=history, **changes)
