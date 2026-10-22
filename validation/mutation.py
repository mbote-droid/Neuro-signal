"""Mutation testing of the test suite: break the code on purpose and check
that the tests notice (playbook §0.4, "validate the validator").

Each mutant is a one-line edit to the package that a realistic bug could
make. The named test files run against the mutated copy; a mutant that
leaves them green has *survived* and means a test is missing.

    python validation/mutation.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation.common import ROOT, write_result

# (id, file, original, replacement, test files that must fail)
MUTANTS = [
    ("filtfilt_style_double_pass", "preprocessing/filters.py",
     "    return np.asarray(y[..., pad : pad + x.shape[-1]], dtype=np.float64)",
     "    y = signal.oaconvolve(y, h, mode='same', axes=-1)\n    return np.asarray(y[..., pad : pad + x.shape[-1]], dtype=np.float64)",
     ["tests/test_filters.py"]),
    ("causal_instead_of_zero_phase", "preprocessing/filters.py",
     'mode="same", axes=-1)', 'mode="full", axes=-1)[..., : padded.shape[-1]]',
     ["tests/test_filters.py"]),
    ("mad_constant_wrong", "preprocessing/qc.py",
     "MAD_TO_SD = 1.4826", "MAD_TO_SD = 0.6745", ["tests/test_qc.py", "tests/test_detection.py"]),
    ("flat_check_disabled", "preprocessing/qc.py",
     "            if run > self.max_duration_s:", "            if run > 1e9:", ["tests/test_qc.py"]),
    ("car_includes_bad_channels", "preprocessing/reference.py",
     "        mean = rec.data[good].mean(axis=0)", "        mean = rec.data.mean(axis=0)",
     ["tests/test_reference.py"]),
    ("car_on_bipolar", "preprocessing/reference.py",
     "self.applied = not rec.is_bipolar and len(good) >= 3", "self.applied = len(good) >= 3",
     ["tests/test_reference.py"]),
    ("wpli_without_abs_denominator", "features/connectivity.py",
     "    abs_total = np.abs(imag).sum(axis=0)", "    abs_total = np.abs(imag.sum(axis=0))",
     ["tests/test_connectivity.py"]),
    ("dwpli_biased", "features/connectivity.py",
     "(total**2 - sq_total) / dden", "total**2 / abs_total**2", ["tests/test_connectivity.py"]),
    ("exponent_sign_flip", "features/aperiodic.py",
     "    return float(icpt), float(-slope)", "    return float(icpt), float(slope)",
     ["tests/test_aperiodic.py"]),
    ("welch_no_overlap", "features/spectral.py",
     "    nover = round(overlap * nper)", "    nover = 0", ["tests/test_spectral.py"]),
    ("rhythm_gate_off", "detection/seizure.py",
     "        if p.rhythm_hz[0] <= f_dom <= p.rhythm_hz[1]:", "        if True:",
     ["tests/test_detection.py"]),
    ("checker_ignores_precision", "explain/checker.py",
     "    half = 0.5 * 10.0 ** (int(exponent or 0) - decimals)", "    half = 0.5",
     ["tests/test_explain.py"]),
    ("checker_ascii_minus_only", "explain/checker.py",
     'MINUS = "-\\u2010\\u2011\\u2012\\u2013\\u2212\\ufe63\\uff0d"', 'MINUS = "-"',
     ["tests/test_explain.py"]),
    ("checker_no_uncited", "explain/checker.py",
     "        if n.start() not in consumed:", "        if False:", ["tests/test_explain.py"]),
    ("checker_no_diagnostic", "explain/checker.py",
     '    findings += [Finding("DIAGNOSTIC", d.group()) for d in DIAGNOSTIC.finditer(stripped)]',
     "    pass", ["tests/test_explain.py"]),
    ("reader_keeps_volts", "io/readers.py",
     'data = raw.get_data(units="uV")', "data = raw.get_data()", ["tests/test_io.py"]),
    ("size_limit_off", "io/readers.py", "    if size > max_bytes:", "    if False:",
     ["tests/test_io.py"]),
    ("metrics_random_run_id", "pipeline.py",
     '        "config": cfg.to_dict(),', '        "config": cfg.to_dict(),\n        "run_id": __import__("os").urandom(4).hex(),',
     ["tests/test_pipeline.py"]),
]  # fmt: skip


def run_mutant(mid: str, rel: str, old: str, new: str, tests: list[str]) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(
            ROOT, work, ignore=shutil.ignore_patterns(".git", ".venv", "data", "results", "out")
        )
        (work / "results").symlink_to(ROOT / "results")
        target = work / "src" / "neurosignal" / rel
        src = target.read_text()
        if old not in src:
            return {"id": mid, "status": "NOT_APPLIED", "reason": "pattern not found"}
        target.write_text(src.replace(old, new, 1))
        env_py = f"{work / 'src'}:{work}"
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", *tests],
            cwd=work,
            check=False,
            capture_output=True,
            text=True,
            env={"PYTHONPATH": env_py, "PATH": "/usr/bin:/bin", "HOME": tmp},
            timeout=900,
        )
        status = "KILLED" if proc.returncode != 0 else "SURVIVED"
        tail = proc.stdout.strip().splitlines()[-1:] if proc.stdout else []
        return {"id": mid, "file": rel, "tests": tests, "status": status, "pytest": tail}


def main() -> None:
    rows = []
    for m in MUTANTS:
        r = run_mutant(*m)
        print(f"{r['id']}: {r['status']}", flush=True)
        rows.append(r)
    killed = sum(r["status"] == "KILLED" for r in rows)
    write_result(
        "mutation",
        {
            "mutants": len(rows),
            "killed": killed,
            "survived": [r["id"] for r in rows if r["status"] == "SURVIVED"],
            "not_applied": [r["id"] for r in rows if r["status"] == "NOT_APPLIED"],
            "rows": rows,
        },
    )


if __name__ == "__main__":
    main()
