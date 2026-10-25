"""Re-referencing (F-07, ADR-005, EQUATIONS §3)."""

from __future__ import annotations

from typing import Any

import numpy as np

from neurosignal.core.recording import Recording
from neurosignal.core.stage import Stage


class CommonAverage(Stage):
    """x_i - mean over good channels, for referential montages only.

    The average excludes bad channels so one disconnected electrode cannot
    leak into every channel. Bipolar montages pass through unchanged.
    """

    name = "reference"

    def __init__(self) -> None:
        self.applied = False

    def process(self, rec: Recording) -> Recording:
        # the average is taken over good EEG channels only: an ECG channel would
        # leak the heartbeat into every channel (ISSUE-017)
        eeg = set(rec.eeg_channels)
        good = rec.index([c for c in rec.good_channels if c in eeg])
        self.applied = not rec.is_bipolar and len(good) >= 3
        if not self.applied:
            return rec
        mean = rec.data[good].mean(axis=0)
        return rec.evolve(data=rec.data - mean[np.newaxis, :])

    def params(self) -> dict[str, Any]:
        return {
            "method": "common average (good EEG channels)"
            if self.applied
            else "none (bipolar or <3 good channels)",
            "applied": self.applied,
        }
