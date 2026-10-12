"""Phase coupling between channels (F-11, ADR-007, EQUATIONS §6).

For epochs e and frequency bins f in the band, with cross-spectrum
S_ij(e, f) = X_i(e, f) conj(X_j(e, f)):

    PLV    = mean_f | mean_e S / |S| |
    wPLI   = mean_f | mean_e Im S | / mean_e |Im S|
    dwPLI2 = mean_f ((sum Im S)^2 - sum (Im S)^2) / ((sum |Im S|)^2 - sum (Im S)^2)

wPLI is biased upwards with few epochs (about 0.2 at 60 epochs with no
coupling at all, docs/FINDINGS.md); the debiased squared estimator of Vinck
et al. (2011) has expectation near zero under the null and is reported as
the primary measure.

Zero-lag mixing (volume conduction) produces real-valued cross-spectra,
so Im S ~ 0 and wPLI stays near zero while PLV is inflated.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal

from neurosignal.core.recording import FloatArray, Recording


@dataclass(frozen=True)
class Connectivity:
    channels: tuple[str, ...]
    wpli: FloatArray  # (n, n), symmetric, nan on the diagonal
    dwpli: FloatArray  # debiased squared wPLI
    plv: FloatArray
    band: tuple[float, float]
    n_epochs: int

    def upper(self, which: str = "wpli") -> FloatArray:
        mat = {"wpli": self.wpli, "dwpli": self.dwpli, "plv": self.plv}[which]
        i, j = np.triu_indices(len(self.channels), k=1)
        return np.asarray(mat[i, j])


def epoch_spectra(
    data: FloatArray,
    sfreq: float,
    epoch_s: float,
    band: tuple[float, float],
    max_s: float,
    exclude: list[tuple[float, float]] | None = None,
) -> tuple[np.ndarray, FloatArray]:
    """Hann-tapered FFTs of non-overlapping epochs, restricted to band.

    Returns (n_epochs, n_channels, n_band_freqs) complex and the frequencies.
    Epochs overlapping an `exclude` interval (s) are dropped; when more than
    max_s of epochs remain, they are spread evenly over the recording.
    """
    n = round(epoch_s * sfreq)
    candidates = np.arange(data.shape[-1] // n) * n
    for a, b in exclude or []:
        t0, t1 = candidates / sfreq, (candidates + n) / sfreq
        candidates = candidates[~((t1 > a) & (t0 < b))]
    if candidates.size < 2:
        raise ValueError("need at least two epochs for phase statistics")
    keep = min(candidates.size, max(2, int(max_s // epoch_s)))
    starts = candidates[np.linspace(0, candidates.size - 1, keep).astype(int)]
    epochs = np.stack([data[:, s : s + n] for s in starts])
    epochs = epochs - epochs.mean(axis=-1, keepdims=True)
    taper = signal.windows.hann(n, sym=False)
    spec = np.fft.rfft(epochs * taper, axis=-1)
    freqs = np.fft.rfftfreq(n, 1 / sfreq)
    m = (freqs >= band[0]) & (freqs <= band[1])
    return spec[..., m], np.asarray(freqs[m])


def phase_coupling(
    rec: Recording,
    band: tuple[float, float] = (8.0, 12.0),
    epoch_s: float = 2.0,
    max_s: float = 600.0,
    channels: tuple[str, ...] | None = None,
    exclude: list[tuple[float, float]] | None = None,
) -> Connectivity:
    chans = channels if channels is not None else rec.good_channels
    x = rec.data[rec.index(list(chans))]
    spec, _ = epoch_spectra(x, rec.sfreq, epoch_s, band, max_s, exclude)
    cross = spec[:, :, np.newaxis, :] * np.conj(spec[:, np.newaxis, :, :])  # (e, i, j, f)
    imag = cross.imag
    total = imag.sum(axis=0)
    abs_total = np.abs(imag).sum(axis=0)
    sq_total = (imag**2).sum(axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        wpli_f = np.where(abs_total > 0, np.abs(total) / abs_total, 0.0)
        dden = abs_total**2 - sq_total
        dwpli_f = np.where(dden > 0, (total**2 - sq_total) / dden, 0.0)
        unit = np.where(np.abs(cross) > 0, cross / np.abs(cross), 0)
    mats = [wpli_f.mean(axis=-1), dwpli_f.mean(axis=-1), np.abs(unit.mean(axis=0)).mean(axis=-1)]
    for mat in mats:
        np.fill_diagonal(mat, np.nan)
    return Connectivity(
        channels=tuple(chans),
        wpli=mats[0],
        dwpli=mats[1],
        plv=mats[2],
        band=band,
        n_epochs=int(spec.shape[0]),
    )
