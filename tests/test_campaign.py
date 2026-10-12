"""P-01, R-04, V-09: the committed validation evidence is complete and intact."""

from __future__ import annotations

import hashlib
import json

import pytest

from validation.campaign import parse_summary
from validation.common import RESULTS

EXPECTED = ["aperiodic", "h1_confound", "qc", "detection_synthetic", "connectivity", "checker",
            "chbmit", "chbmit_h5_registered", "chbmit_heldout", "resources", "detector_tuning",
            "mutation"]  # fmt: skip


def _load(name):
    path = RESULTS / f"{name}.json"
    if not path.exists():
        pytest.skip(f"{name}.json not generated; run `make validate`")
    return json.loads(path.read_text())


@pytest.mark.parametrize("name", EXPECTED)
def test_result_files_carry_provenance(name):
    """R-04."""
    prov = _load(name)["provenance"]
    assert prov["versions"]["neurosignal"]
    assert "commit" in prov["git"]


def test_manifest_matches_result_files():
    """R-04: every listed hash matches the file on disk."""
    manifest = RESULTS / "MANIFEST.sha256"
    if not manifest.exists():
        pytest.skip("no manifest; run `make report`")
    for line in manifest.read_text().splitlines():
        digest, name = line.split()
        assert hashlib.sha256((RESULTS / name).read_bytes()).hexdigest() == digest, name


def test_hypotheses_h1_and_h5_have_verdicts():
    """V-09: evaluated and reported, accepted or rejected."""
    assert isinstance(_load("h1_confound")["H1_accepted"], bool)
    assert isinstance(_load("chbmit_h5_registered")["H5_accepted"], bool)
    assert isinstance(_load("chbmit_heldout")["H6_accepted"], bool)


def test_resource_budget():
    """P-01."""
    r = _load("resources")
    assert r["runtime_s"] <= 300
    assert r["peak_rss_mb"] <= 2048


def test_summary_parser(tmp_path):
    p = tmp_path / "s.txt"
    p.write_text(
        "File Name: a.edf\nNumber of Seizures in File: 0\n\n"
        "File Name: b.edf\nNumber of Seizures in File: 2\n"
        "Seizure 1 Start Time: 10 seconds\nSeizure 1 End Time: 20 seconds\n"
        "Seizure 2 Start Time: 30 seconds\nSeizure 2 End Time: 45 seconds\n"
    )
    assert parse_summary(p) == {"a.edf": [], "b.edf": [(10.0, 20.0), (30.0, 45.0)]}
