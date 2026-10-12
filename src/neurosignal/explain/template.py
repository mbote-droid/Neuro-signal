"""Deterministic explainer (F-14): every number carries its citation.

The text explains what the numbers mean for a reader who knows some EEG,
including the two interpretation traps the pipeline was built around
(aperiodic shifts read as oscillations; zero-lag mixing read as coupling).
"""

from __future__ import annotations

from typing import Any

DISCLAIMER = (
    "**Research use only.** This summary was produced by validated software, "
    "not by a clinician. It is not a medical device and makes no clinical "
    "statements; candidate events need expert review."
)


def _num(x: float, decimals: int) -> str:
    return f"{x:.{decimals}f}"


def _c(value: Any, key: str, decimals: int = 2) -> str:
    """A value followed by its citation; ints and text are written as they are."""
    if isinstance(value, bool | str | int):
        return f"{value} [[{key}]]"
    return f"{_num(float(value), decimals)} [[{key}]]"


def _recording(m: dict[str, Any]) -> str:
    r = m["recording"]
    return (
        f"The recording has {_c(r['n_channels'], 'recording.n_channels')} channels, lasts "
        f"{_c(r['duration_s'], 'recording.duration_s', 1)} s, was sampled at "
        f"{_c(r['sfreq_hz'], 'recording.sfreq_hz', 0)} Hz and uses a "
        f"{_c(r['montage'], 'recording.montage')} montage."
    )


def _quality(m: dict[str, Any]) -> str:
    q = m["qc"]
    bad = ", ".join(q["bad_channels"]) if q["bad_channels"] else "none"
    text = (
        f"Quality control marked {_c(q['n_bad'], 'qc.n_bad')} channels as bad "
        f"({bad} [[qc.bad_channels]]); they are excluded from every measure below. "
    )
    after = q["line_noise_ratio_after_median"]
    if after is not None:
        lo, hi = q["line_noise_reference_band_hz"]
        text += (
            "The median line-noise ratio (power near mains over "
            f"{_c(lo, 'qc.line_noise_reference_band_hz.0', 0)} to "
            f"{_c(hi, 'qc.line_noise_reference_band_hz.1', 0)} Hz power) went from "
            f"{_c(q['line_noise_ratio_before_median'], 'qc.line_noise_ratio_before_median', 4)} "
            f"before cleaning to {_c(after, 'qc.line_noise_ratio_after_median', 4)} after."
        )
    if q["rereferenced"]:
        text += " Channels were re-referenced to the common average of good channels."
    else:
        text += " The montage was kept as recorded (no common average reference)."
    return text


def _spectrum(m: dict[str, Any]) -> str:
    ap = m["aperiodic"]
    if ap["exponent"]["mean"] is None:
        return "No spectrum could be parameterised (no good channels with a reliable fit)."
    ex, r2 = ap["exponent"], ap["r_squared"]
    text = (
        "The aperiodic (power-law background) exponent averaged "
        f"{_c(ex['mean'], 'aperiodic.exponent.mean')} (range "
        f"{_c(ex['min'], 'aperiodic.exponent.min')} to {_c(ex['max'], 'aperiodic.exponent.max')}) "
        f"with mean fit R² {_c(r2['mean'], 'aperiodic.r_squared.mean', 3)}. "
    )
    if ap["n_poor_fits"]:
        names = ", ".join(ap["poor_fit_channels"])
        text += (
            f"{_c(ap['n_poor_fits'], 'aperiodic.n_poor_fits')} channels had an unreliable fit "
            f"({names} [[aperiodic.poor_fit_channels]]) and are left out of these averages. "
        )
    if m["spectral"]["event_windows_excluded"]:
        text += "Windows inside detected events were excluded, so these describe the background. "
    return text + _alpha(m)


def _alpha(m: dict[str, Any]) -> str:
    ap = m["aperiodic"]
    n_alpha = ap["n_channels_with_alpha"]
    if n_alpha:
        freq, power = ap["alpha_peak_freq_hz"]["mean"], ap["alpha_peak_power"]["mean"]
        text = (
            f"An alpha peak was found in {_c(n_alpha, 'aperiodic.n_channels_with_alpha')} "
            f"channels, at {_c(freq, 'aperiodic.alpha_peak_freq_hz.mean', 1)} Hz on average, "
            f"rising {_c(power, 'aperiodic.alpha_peak_power.mean')} log10 units above the "
            "aperiodic fit. "
        )
    else:
        text = "No channel showed an alpha peak above the aperiodic fit. "
    lo, hi = m["config"]["alpha_band_hz"]
    bp = m["spectral"]["alpha_band_power_uv2"]["mean"]
    return text + (
        f"Canonical {_c(lo, 'config.alpha_band_hz.0', 0)} to "
        f"{_c(hi, 'config.alpha_band_hz.1', 0)} Hz band power averaged "
        f"{_c(bp, 'spectral.alpha_band_power_uv2.mean')} µV². "
        "Band power mixes the oscillation with the aperiodic background: a change in the "
        "exponent alone changes band power, so compare peak power, not band power, when the "
        "question is about the oscillation."
    )


def _coupling(m: dict[str, Any]) -> str:
    c = m["connectivity"]
    if c is None:
        return "Coupling was not computed (fewer than two good channels)."
    text = (
        f"Across {_c(c['n_epochs'], 'connectivity.n_epochs')} epochs, alpha-band debiased wPLI "
        f"averaged {_c(c['dwpli_mean'], 'connectivity.dwpli_mean', 3)}, while PLV averaged "
        f"{_c(c['plv_mean'], 'connectivity.plv_mean', 3)}. PLV is inflated by volume conduction "
        "(the same source seen by many electrodes at zero lag); wPLI ignores zero-lag coupling, so "
        "it is the measure to read."
    )
    if c["top_pairs"]:
        p = c["top_pairs"][0]
        text += (
            f" The most strongly coupled pair was {p['a']} [[connectivity.top_pairs.0.a]] and "
            f"{p['b']} [[connectivity.top_pairs.0.b]] "
            f"(debiased wPLI {_c(p['dwpli'], 'connectivity.top_pairs.0.dwpli', 3)})."
        )
    return text


def _events(m: dict[str, Any]) -> str:
    e = m["events"]
    found = f"The line-length detector found {_c(e['n_events'], 'events.n_events')} rhythmic"
    if e["n_events"] == 0:
        return found + " seizure-like events."
    total = _c(e["total_duration_s"], "events.total_duration_s", 0)
    text = f"{found} seizure-like events, {total} s in total:"
    for i, ev in enumerate(e["list"]):
        k = f"events.list.{i}"
        text += (
            f"\n- from {_c(ev['onset_s'], k + '.onset_s', 0)} s to "
            f"{_c(ev['offset_s'], k + '.offset_s', 0)} s, dominant rhythm "
            f"{_c(ev['dominant_freq_hz'], k + '.dominant_freq_hz', 1)} Hz "
            f"({_c(ev['n_channels'], k + '.n_channels')} channels involved)"
        )
    return text + "\n\nThese are candidates for expert review, not findings."


def explain(metrics: dict[str, Any]) -> str:
    sections = [
        ("Summary", DISCLAIMER),
        ("Recording", _recording(metrics)),
        ("Quality", _quality(metrics)),
        ("Spectrum", _spectrum(metrics)),
        ("Coupling", _coupling(metrics)),
        ("Events", _events(metrics)),
    ]
    return "\n\n".join(f"### {title}\n\n{body}" for title, body in sections) + "\n"
