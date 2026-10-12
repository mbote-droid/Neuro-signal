"""Choose the detector thresholds on synthetic tuning seeds only (ADR-008, V-10).

Selection rule, fixed before running: among settings with at most 1 false
detection per hour on the tuning set, take the highest sensitivity; break
ties by the higher z threshold, then the longer minimum duration, then the
narrower rhythm gate (the more conservative setting). CHB-MIT is never
touched here.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from neurosignal.core.config import PipelineConfig
from neurosignal.detection.events import Interval, score_events
from neurosignal.detection.seizure import (
    DetectorParams,
    band_limit,
    events_from_z,
    line_length_z,
    rhythm_gate,
)
from neurosignal.pipeline import preprocess
from neurosignal.synth.eeg import make_recording
from validation.common import TUNING_SEEDS, detection_spec, write_result

Z_GRID = (2.5, 3.0, 4.0, 5.0)
FRACTION_GRID = (0.05, 0.1, 0.2)
MIN_DURATION_GRID = (4.0, 6.0, 8.0, 10.0, 15.0)
# rhythm gate upper limit: delta-alpha (13 Hz) or delta-theta (8 Hz); both physiological
RHYTHM_GRID = ((2.0, 13.0), (2.0, 8.0))
MAX_FALSE_PER_HOUR = 1.0


def main() -> None:
    cfg = PipelineConfig()
    cached = []
    for seed in TUNING_SEEDS:
        rec, gt = make_recording(seed, detection_spec(seed))
        clean = preprocess(rec, cfg)
        chans = clean.good_channels
        x = band_limit(clean.data[clean.index(list(chans))], clean.sfreq, DetectorParams().band_hz)
        z = line_length_z(x, clean.sfreq, 2.0, 1.0)
        truth = [Interval(e.onset_s, e.offset_s) for e in gt.events]
        cached.append((x, z, chans, truth, rec.duration_s, clean.sfreq))
        print(f"seed {seed} prepared", file=sys.stderr)
    rows = []
    grid = itertools.product(Z_GRID, FRACTION_GRID, MIN_DURATION_GRID, RHYTHM_GRID)
    for zt, frac, mind, rhythm in grid:
        p = DetectorParams(
            z_threshold=zt, channel_fraction=frac, min_duration_s=mind, rhythm_hz=rhythm
        )
        hits = n_true = false = 0
        hours = 0.0
        for x, z, chans, truth, dur, sfreq in cached:
            cands = events_from_z(z, chans, p)
            det = [e.interval() for e in rhythm_gate(cands, x, chans, sfreq, p)]
            sc = score_events(truth, det, dur)
            hits += sc.hits
            n_true += sc.n_true
            false += sc.false_detections
            hours += sc.hours
        rows.append(
            {
                "z_threshold": zt,
                "channel_fraction": frac,
                "min_duration_s": mind,
                "rhythm_hz": list(rhythm),
                "sensitivity": hits / n_true,
                "false_per_hour": false / hours,
                "hits": hits,
                "n_true": n_true,
                "false_detections": false,
                "hours": hours,
            }
        )
    feasible = [r for r in rows if r["false_per_hour"] <= MAX_FALSE_PER_HOUR]
    if not feasible:
        write_result("detector_tuning_infeasible", {"seeds": [TUNING_SEEDS.start, TUNING_SEEDS.stop - 1], "grid": rows})
        raise SystemExit("no setting meets the false-detection constraint; grid saved")
    best = max(
        feasible,
        key=lambda r: (
            r["sensitivity"],
            r["z_threshold"],
            r["min_duration_s"],
            -r["rhythm_hz"][1],
            -r["channel_fraction"],
        ),
    )
    print(best)
    write_result(
        "detector_tuning",
        {
            "seeds": [TUNING_SEEDS.start, TUNING_SEEDS.stop - 1],
            "rule": __doc__,
            "grid": rows,
            "selected": best,
        },
    )


if __name__ == "__main__":
    main()
