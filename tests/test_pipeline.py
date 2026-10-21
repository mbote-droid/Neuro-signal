"""F-13, R-01, R-02: outputs, determinism, provenance."""

from __future__ import annotations

import json
import subprocess
import sys

from neurosignal.io.readers import write_npz
from neurosignal.report.build import build_report

_RUN = (
    "import sys;from pathlib import Path;from neurosignal.report.build import build_report;"
    "build_report(Path(sys.argv[1]), Path(sys.argv[2]))"
)


def test_report_outputs_written(tmp_path, synth_pair):
    """F-13."""
    rec, _ = synth_pair
    src = tmp_path / "in.npz"
    write_npz(rec, src)
    res = build_report(src, tmp_path / "out")
    for name in ("metrics.json", "report.md", "report.html", "explanation.md", "run.json"):
        assert (tmp_path / "out" / name).is_file()
    for fig in ("spectrum", "channels", "connectivity", "events"):
        assert (tmp_path / "out" / "figures" / f"{fig}.png").is_file()
    html = (tmp_path / "out" / "report.html").read_text()
    assert "Research use only" in html and "Claim check passed" in html
    assert res.check.ok


def test_metrics_byte_identical_across_processes(tmp_path, synth_pair):
    """R-01."""
    rec, _ = synth_pair
    src = tmp_path / "in.npz"
    write_npz(rec, src)
    for k in (1, 2):
        subprocess.run([sys.executable, "-c", _RUN, str(src), str(tmp_path / f"o{k}")], check=True)
    a = (tmp_path / "o1" / "metrics.json").read_bytes()
    b = (tmp_path / "o2" / "metrics.json").read_bytes()
    assert a == b


def test_provenance_and_processing_history(tmp_path, synth_pair):
    """R-02: versions, commit, input hash, configuration; every stage's parameters."""
    rec, _ = synth_pair
    src = tmp_path / "in.npz"
    write_npz(rec, src)
    build_report(src, tmp_path / "out")
    m = json.loads((tmp_path / "out" / "metrics.json").read_text())
    prov = m["provenance"]
    assert set(prov["versions"]) >= {"neurosignal", "numpy", "scipy", "mne"}
    assert "commit" in prov["git"] and "dirty" in prov["git"]
    assert len(prov["input_sha256"]) == 64
    assert m["config"]["seed"] == 0
    stages = [s["stage"] for s in m["processing"]]
    assert stages == ["read", "qc_flat", "filter", "qc_amplitude", "reference"]
    filt = next(s for s in m["processing"] if s["stage"] == "filter")
    assert filt["highpass_hz"] == 0.5 and filt["lowpass_hz"] == 45.0
    assert "zero-phase" in filt["type"]


def test_html_escapes_untrusted_explanation(metrics):
    from neurosignal.report.render import _md_to_html

    out = _md_to_html("<script>alert(1)</script> [[qc.n_bad]]", metrics)
    assert "<script>" not in out and "&lt;script&gt;" in out


def test_model_markdown_headings_and_bullets_render(metrics):
    """LLMs write '##' headings and '*' bullets; neither may show as raw markdown."""
    from neurosignal.report.render import _md_to_html

    out = _md_to_html("## Summary\n### Quality\n#### Detail\n* one\n- two\n#hashtag", metrics)
    assert "<h3>Summary</h3>" in out and "<h3>Quality</h3>" in out
    assert "<h4>Detail</h4>" in out
    assert "<li>one</li>" in out and "<li>two</li>" in out
    assert "##" not in out
    assert "<p>#hashtag</p>" in out  # no space after '#': not a heading
