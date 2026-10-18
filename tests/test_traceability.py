"""Every requirement ID in docs/REQUIREMENTS.md is named by at least one test."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_every_requirement_has_a_test():
    reqs = set(
        re.findall(r"^\| ([FVPSR]-\d\d) \|", (ROOT / "docs/REQUIREMENTS.md").read_text(), re.M)
    )
    assert len(reqs) >= 30
    tests = "".join(p.read_text() for p in (ROOT / "tests").glob("test_*.py"))
    missing = sorted(r for r in reqs if r not in tests)
    assert not missing, f"requirements without a test: {missing}"
