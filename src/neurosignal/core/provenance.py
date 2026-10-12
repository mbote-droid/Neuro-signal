"""Provenance attached to every metrics file and validation result (R-02, R-04).

Deliberately free of wall-clock time so that the record itself is
deterministic (ADR-010); run timing is written separately.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import platform
import subprocess
from pathlib import Path
from typing import Any

import neurosignal

_PACKAGES = ("numpy", "scipy", "mne", "matplotlib")
_REPO = Path(__file__).resolve().parents[3]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def git_state() -> dict[str, Any]:
    def git(*args: str) -> str | None:
        try:
            out = subprocess.run(
                ["git", *args], cwd=_REPO, capture_output=True, text=True, check=True, timeout=10
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip()

    commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain", "--untracked-files=no")
    return {"commit": commit, "dirty": bool(status) if status is not None else None}


def versions() -> dict[str, str | None]:
    out: dict[str, str | None] = {"neurosignal": neurosignal.__version__}
    for pkg in _PACKAGES:
        try:
            out[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            out[pkg] = None
    return out


def collect(**extra: Any) -> dict[str, Any]:
    return {
        "git": git_state(),
        "versions": versions(),
        "python": platform.python_version(),
        **extra,
    }
