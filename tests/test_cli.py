"""F-17: every command runs."""

from __future__ import annotations

import json

from neurosignal.cli import main


def test_synth_report_explain_check_info(tmp_path, capsys):
    npz = tmp_path / "s.npz"
    assert (
        main(["synth", "--seed", "1", "--out", str(npz), "--duration", "120", "--events", "1"]) == 0
    )
    assert json.loads(npz.with_suffix(".truth.json").read_text())["seed"] == 1
    assert main(["info", str(npz)]) == 0
    assert '"n_channels": 19' in capsys.readouterr().out
    out = tmp_path / "rep"
    assert main(["report", str(npz), "--out", str(out)]) == 0
    assert main(["explain", str(out / "metrics.json")]) == 0
    assert main(["check", str(out / "explanation.md"), str(out / "metrics.json")]) == 0
    bad = tmp_path / "bad.md"
    bad.write_text("This EEG shows epilepsy in 3 channels.")
    assert main(["check", str(bad), str(out / "metrics.json")]) == 1


def test_refused_file_exit_code(tmp_path, capsys):
    p = tmp_path / "x.txt"
    p.write_text("hello")
    assert main(["info", str(p)]) == 2
    assert "refused" in capsys.readouterr().err


def test_config_override(tmp_path):
    from neurosignal.core.config import PipelineConfig

    cfg = tmp_path / "c.toml"
    cfg.write_text("lowpass_hz = 40.0\nalpha_band_hz = [8.0, 13.0]\n")
    c = PipelineConfig.from_toml(cfg)
    assert c.lowpass_hz == 40.0 and c.alpha_band_hz == (8.0, 13.0)
    cfg.write_text("lowpas_hz = 40.0\n")
    try:
        PipelineConfig.from_toml(cfg)
    except ValueError as exc:
        assert "unknown configuration keys" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("typo in config was accepted")
