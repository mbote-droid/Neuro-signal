"""`neurosignal` command line (F-17). Every workflow is one command."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from neurosignal.core.config import PipelineConfig
from neurosignal.explain.checker import check
from neurosignal.io.readers import RefusedFile, read, write_npz
from neurosignal.synth.eeg import SynthSpec, make_recording


def _config(path: str | None) -> PipelineConfig:
    return PipelineConfig.from_toml(Path(path)) if path else PipelineConfig()


def cmd_report(a: argparse.Namespace) -> int:
    from neurosignal.report.build import build_report

    res = build_report(
        Path(a.file),
        Path(a.out),
        _config(a.config),
        explainer=a.explainer,
        max_bytes=int(a.max_mb * 1024 * 1024),
    )
    m = res.metrics
    print(f"report: {res.outdir / 'report.html'}")
    print(
        f"  {m['recording']['n_channels']} channels, {m['recording']['duration_s']} s, "
        f"{m['qc']['n_bad']} bad, {m['events']['n_events']} event candidate(s)"
    )
    print(f"  explanation: {res.source}; claim check {'passed' if res.check.ok else 'FAILED'}")
    return 0 if res.check.ok else 1


def cmd_synth(a: argparse.Namespace) -> int:
    spec = SynthSpec(
        duration_s=a.duration,
        n_events=a.events,
        snr_db=a.snr,
        n_flat=a.flat,
        n_noisy=a.noisy,
        blinks_per_min=a.blinks,
        muscle_per_min=a.muscle,
    )
    rec, gt = make_recording(a.seed, spec)
    write_npz(rec, a.out)
    truth = {
        "seed": a.seed,
        "bad_channels": gt.bad_channels,
        "events": [{"onset_s": e.onset_s, "offset_s": e.offset_s, "channels": list(e.channels)}
                   for e in gt.events],
        "mean_exponent": sum(s.exponent for s in gt.spectra.values()) / len(gt.spectra),
    }  # fmt: skip
    truth_path = Path(a.out).with_suffix(".truth.json")
    truth_path.write_text(json.dumps(truth, indent=2) + "\n")
    print(f"wrote {a.out} and {truth_path} (ground truth kept separate)")
    return 0


def cmd_explain(a: argparse.Namespace) -> int:
    from neurosignal.report.build import explain

    metrics = json.loads(Path(a.metrics).read_text())
    text, result, source = explain(metrics, a.explainer)
    print(text)
    print(f"<!-- source: {source}; claim check {'passed' if result.ok else 'FAILED'} -->")
    return 0 if result.ok else 1


def cmd_check(a: argparse.Namespace) -> int:
    metrics = json.loads(Path(a.metrics).read_text())
    result = check(Path(a.explanation).read_text(), metrics)
    for f in result.findings:
        print(f"{f.code}\t{f.detail}")
    print(f"{'PASS' if result.ok else 'FAIL'}: {result.n_citations} citations, "
          f"{len(result.findings)} finding(s)")  # fmt: skip
    return 0 if result.ok else 1


def cmd_info(a: argparse.Namespace) -> int:
    rec = read(a.file)
    print(json.dumps({
        "channels": list(rec.channels), "n_channels": rec.n_channels, "sfreq_hz": rec.sfreq,
        "duration_s": rec.duration_s, "montage": "bipolar" if rec.is_bipolar else "referential",
        "annotations": len(rec.annotations), "sha256": rec.source_sha256,
    }, indent=2))  # fmt: skip
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="neurosignal", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="analyse an EEG file and write a validated report")
    r.add_argument("file")
    r.add_argument("--out", default="out")
    r.add_argument("--config", help="TOML file overriding PipelineConfig fields")
    r.add_argument("--explainer", choices=["template", "llm"], default="template")
    r.add_argument("--max-mb", type=float, default=2048.0)
    r.set_defaults(func=cmd_report)

    s = sub.add_parser("synth", help="write a synthetic recording with known ground truth")
    s.add_argument("--seed", type=int, default=0)
    s.add_argument("--out", default="synthetic.npz")
    s.add_argument("--duration", type=float, default=300.0)
    s.add_argument("--events", type=int, default=2)
    s.add_argument("--snr", type=float, default=6.0)
    s.add_argument("--flat", type=int, default=1)
    s.add_argument("--noisy", type=int, default=1)
    s.add_argument("--blinks", type=float, default=10.0)
    s.add_argument("--muscle", type=float, default=1.0)
    s.set_defaults(func=cmd_synth)

    e = sub.add_parser("explain", help="explain an existing metrics.json")
    e.add_argument("metrics")
    e.add_argument("--explainer", choices=["template", "llm"], default="template")
    e.set_defaults(func=cmd_explain)

    c = sub.add_parser("check", help="check an explanation against metrics.json")
    c.add_argument("explanation")
    c.add_argument("metrics")
    c.set_defaults(func=cmd_check)

    i = sub.add_parser("info", help="print a file's channels, rate, duration and montage")
    i.add_argument("file")
    i.set_defaults(func=cmd_info)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.func(args))
    except RefusedFile as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
