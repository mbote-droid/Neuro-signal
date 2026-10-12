"""Pipeline configuration: every tunable number in one validated place.

Defaults are the values justified in docs/EQUATIONS.md. A TOML file may
override any field; unknown keys are an error, so a typo cannot silently
leave a default in force.
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PipelineConfig:
    # quality control (F-03, F-04, F-05)
    flat_tolerance_uv: float = 0.1
    flat_max_duration_s: float = 5.0
    noisy_mad_ratio: float = 5.0
    low_mad_ratio: float = 0.2
    line_freq_hz: float = 50.0
    # filtering (F-06)
    highpass_hz: float = 0.5
    lowpass_hz: float = 45.0
    notch_width_hz: float = 2.0
    # spectra (F-08 - F-10)
    welch_window_s: float = 2.0
    welch_overlap: float = 0.5
    fit_range_hz: tuple[float, float] = (2.0, 40.0)
    max_peaks: int = 4
    peak_threshold_sd: float = 2.0
    min_peak_height: float = 0.1
    peak_width_limits_hz: tuple[float, float] = (1.0, 8.0)
    alpha_search_hz: tuple[float, float] = (7.0, 14.0)
    alpha_band_hz: tuple[float, float] = (8.0, 12.0)
    min_fit_r_squared: float = 0.8
    max_exponent: float = 4.0
    # connectivity (F-11)
    connectivity_epoch_s: float = 2.0
    max_connectivity_s: float = 600.0
    # event detection (F-12); thresholds chosen on synthetic tuning seeds 0-59 only
    # (ADR-008, results/validation/detector_tuning.json); band limits from physiology
    ll_window_s: float = 2.0
    ll_step_s: float = 1.0
    ll_z_threshold: float = 2.5
    ll_channel_fraction: float = 0.05
    ll_min_duration_s: float = 10.0
    ll_merge_gap_s: float = 5.0
    ll_band_hz: tuple[float, float] = (1.0, 20.0)
    rhythm_band_hz: tuple[float, float] = (2.0, 7.5)
    # reproducibility
    seed: int = 0

    def __post_init__(self) -> None:
        if not 0 < self.highpass_hz < self.lowpass_hz:
            raise ValueError("need 0 < highpass_hz < lowpass_hz")
        if not 0 <= self.welch_overlap < 1:
            raise ValueError("welch_overlap must be in [0, 1)")
        if self.fit_range_hz[0] >= self.fit_range_hz[1]:
            raise ValueError("fit_range_hz must be increasing")
        if not 0 < self.ll_channel_fraction <= 1:
            raise ValueError("ll_channel_fraction must be in (0, 1]")
        if self.max_peaks < 0:
            raise ValueError("max_peaks must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        return {k: list(v) if isinstance(v, tuple) else v for k, v in asdict(self).items()}

    @classmethod
    def from_toml(cls, path: Path) -> PipelineConfig:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> PipelineConfig:
        known = {f.name for f in fields(cls)}
        unknown = set(raw) - known
        if unknown:
            raise ValueError(f"unknown configuration keys: {sorted(unknown)}")
        values = {k: tuple(v) if isinstance(v, list) else v for k, v in raw.items()}
        return cls(**values)  # type: ignore[arg-type]
