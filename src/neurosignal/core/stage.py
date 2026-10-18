"""Stage lifecycle (Template Method) and the Pipeline composite (ADR-001)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

import numpy as np

from neurosignal.core.recording import Recording


class Stage(ABC):
    """validate input -> process -> check invariants -> record parameters."""

    name: str = "stage"

    def __call__(self, rec: Recording) -> Recording:
        self.validate(rec)
        out = self.process(rec)
        self.check(rec, out)
        return out.evolve({"stage": self.name, **self.params()})

    def validate(self, rec: Recording) -> None:
        if not np.all(np.isfinite(rec.data)):
            raise ValueError(f"{self.name}: input contains NaN or infinite samples")

    @abstractmethod
    def process(self, rec: Recording) -> Recording: ...

    def check(self, before: Recording, after: Recording) -> None:
        if after.data.shape[1] != before.data.shape[1]:
            raise AssertionError(f"{self.name} changed the number of samples")
        if not np.all(np.isfinite(after.data)):
            raise AssertionError(f"{self.name} produced NaN or infinite samples")

    def params(self) -> dict[str, Any]:
        return {}


class Identity(Stage):
    """Null Object, for ablations."""

    name = "identity"

    def process(self, rec: Recording) -> Recording:
        return rec


class Pipeline(Stage):
    """A sequence of stages run as one."""

    name = "pipeline"

    def __init__(self, stages: Sequence[Stage]) -> None:
        self.stages = list(stages)

    def __call__(self, rec: Recording) -> Recording:
        for stage in self.stages:
            rec = stage(rec)
        return rec

    def process(self, rec: Recording) -> Recording:  # pragma: no cover - __call__ overrides
        return self(rec)
