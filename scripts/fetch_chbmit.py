"""Download CHB-MIT subsets and verify SHA-256 checksums.

Source: CHB-MIT Scalp EEG Database v1.0.0 (Shoeb 2009; Goldberger et al. 2000),
Open Data Commons Attribution License v1.0, via PhysioNet's open-data mirror
on AWS (s3://physionet-open). Files land in data/raw/chbmit/ (git-ignored)
and are refused if their checksum differs from PhysioNet's SHA256SUMS.txt.

    python scripts/fetch_chbmit.py            # chb01 (H5, development) and chb03 (H6, held out)
    python scripts/fetch_chbmit.py chb03

File rule (pre-registered for H6, PROBLEM_STATEMENT §9): every file the
subject summary lists with at least one seizure, plus the first three files
listed without seizures.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

BASE = "https://physionet-open.s3.amazonaws.com/chbmit/1.0.0"
OUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "chbmit"
SUBJECTS = ("chb01", "chb03")


def select_files(summary: str) -> list[str]:
    """Seizure files plus the first three seizure-free files, in summary order."""
    files: list[tuple[str, int]] = []
    for line in summary.splitlines():
        if line.startswith("File Name:"):
            files.append((line.split(":", 1)[1].strip(), 0))
        elif line.startswith("Number of Seizures in File:") and files:
            files[-1] = (files[-1][0], int(line.split(":", 1)[1]))
    seizure = [f for f, n in files if n > 0]
    free = [f for f, n in files if n == 0][:3]
    return sorted(seizure + free)


def _get(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as r, dest.open("wb") as fh:
        while chunk := r.read(1 << 20):
            fh.write(chunk)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def main(subjects: list[str]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    _get(f"{BASE}/SHA256SUMS.txt", OUT / "SHA256SUMS.txt")
    sums = {}
    for line in (OUT / "SHA256SUMS.txt").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        sums[name.strip()] = digest
    bad = 0
    for subject in subjects:
        summary = OUT / f"{subject}-summary.txt"
        _get(f"{BASE}/{subject}/{subject}-summary.txt", summary)
        bad += _fetch_subject(subject, select_files(summary.read_text()), sums)
    return 1 if bad else 0


def _fetch_subject(subject: str, files: list[str], sums: dict[str, str]) -> int:
    bad = 0
    for name in files:
        dest = OUT / name
        expected = sums[f"{subject}/{name}"]
        if not dest.exists() or _sha256(dest) != expected:
            print(f"downloading {name}")
            _get(f"{BASE}/{subject}/{name}", dest)
        ok = _sha256(dest) == expected
        print(f"{name}: {'OK' if ok else 'CHECKSUM MISMATCH'}")
        if not ok:
            dest.unlink()
            bad += 1
    return bad


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or list(SUBJECTS)))
