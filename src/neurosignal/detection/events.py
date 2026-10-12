"""Event-level scoring by any-overlap (Ziyabari et al. 2017, OVLP)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    onset_s: float
    offset_s: float

    @property
    def duration_s(self) -> float:
        return self.offset_s - self.onset_s

    def overlaps(self, other: Interval) -> bool:
        return self.onset_s < other.offset_s and other.onset_s < self.offset_s


@dataclass(frozen=True)
class EventScore:
    n_true: int
    n_detected: int
    hits: int  # true events overlapped by at least one detection
    false_detections: int  # detections overlapping no true event
    hours: float
    onset_latencies_s: tuple[float, ...]  # detected onset - true onset, per hit

    @property
    def sensitivity(self) -> float:
        return self.hits / self.n_true if self.n_true else float("nan")

    @property
    def false_per_hour(self) -> float:
        return self.false_detections / self.hours if self.hours > 0 else float("nan")


def score_events(truth: list[Interval], detected: list[Interval], duration_s: float) -> EventScore:
    hits = 0
    latencies: list[float] = []
    for t in truth:
        overlapping = [d for d in detected if d.overlaps(t)]
        if overlapping:
            hits += 1
            latencies.append(min(d.onset_s for d in overlapping) - t.onset_s)
    false = sum(1 for d in detected if not any(d.overlaps(t) for t in truth))
    return EventScore(
        n_true=len(truth),
        n_detected=len(detected),
        hits=hits,
        false_detections=false,
        hours=duration_s / 3600.0,
        onset_latencies_s=tuple(latencies),
    )
