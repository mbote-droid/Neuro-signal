"""Shared fixtures: small synthetic recordings with known ground truth."""

from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from neurosignal.pipeline import analyse, build_metrics
from neurosignal.synth.eeg import SynthSpec, make_recording


@pytest.fixture(scope="session")
def synth_pair():
    return make_recording(
        7, SynthSpec(duration_s=180.0, n_events=1, snr_db=10.0, n_flat=1, n_noisy=1)
    )


@pytest.fixture(scope="session")
def analysis(synth_pair):
    rec, _ = synth_pair
    return analyse(rec)


@pytest.fixture(scope="session")
def metrics(analysis) -> dict[str, Any]:
    return build_metrics(analysis)


def write_edf(
    path: Path,
    data: np.ndarray,
    sfreq: int,
    labels: list[str],
    unit: str = "uV",
    patient: str = "X F 01-JAN-1970 Jane_Doe",
    phys_range: float = 3276.7,
) -> None:
    """Minimal EDF writer (1 s records, int16) for reader tests; identifying
    patient and date fields are filled in on purpose."""
    n_sig, n = data.shape
    n_rec = n // sfreq

    def field(value: object, width: int) -> bytes:
        return str(value).ljust(width)[:width].encode("ascii")

    header = b"".join(
        [
            field("0", 8), field(patient, 80), field("Startdate 01-JAN-2020 secret-hospital", 80),
            field("01.01.20", 8), field("10.00.00", 8), field(256 * (n_sig + 1), 8),
            field("", 44), field(n_rec, 8), field(1, 8), field(n_sig, 4),
        ]
    )  # fmt: skip
    per = [
        [field(lab, 16) for lab in labels],
        [field("AgAgCl", 80)] * n_sig,
        [field(unit, 8)] * n_sig,
        [field(-phys_range, 8)] * n_sig,
        [field(phys_range, 8)] * n_sig,
        [field(-32767, 8)] * n_sig,
        [field(32767, 8)] * n_sig,
        [field("", 80)] * n_sig,
        [field(sfreq, 8)] * n_sig,
        [field("", 32)] * n_sig,
    ]
    header += b"".join(b"".join(col) for col in per)
    digital = np.clip(np.round(data / phys_range * 32767), -32767, 32767).astype("<i2")
    body = bytearray()
    for r in range(n_rec):
        for s in range(n_sig):
            body += digital[s, r * sfreq : (r + 1) * sfreq].tobytes()
    path.write_bytes(header + bytes(body))
    assert struct.calcsize("<h") == 2
