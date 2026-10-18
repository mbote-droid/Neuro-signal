# NeuroSignal

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23447346.svg)](https://doi.org/10.5281/zenodo.23447346)
[![CI](https://github.com/mbote-droid/Neuro-signal/actions/workflows/ci.yml/badge.svg)](https://github.com/mbote-droid/Neuro-signal/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](pyproject.toml)
[![uv](https://img.shields.io/badge/deps-uv%20locked-DE5FE9?logo=uv&logoColor=white)](uv.lock)
[![Ruff](https://img.shields.io/badge/lint-ruff-D7FF64?logo=ruff&logoColor=black)](pyproject.toml)
[![mypy strict](https://img.shields.io/badge/types-mypy%20strict-2A6DB2)](pyproject.toml)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-025E8C?logo=dependabot&logoColor=white)](.github/dependabot.yml)
[![MNE](https://img.shields.io/badge/EEG%20I%2FO-MNE--Python-1F4E79)](https://mne.tools)

**Drop an EEG file, get a validated report.** NeuroSignal reads a scalp EEG
recording and produces channel quality, a spectrum split into aperiodic
(1/f) and oscillatory parts, phase coupling that ignores volume conduction,
candidate rhythmic seizure-like events, and a plain-language explanation in
which **every number is mechanically traced to a computed value**. Every
method was tested against synthetic data with known answers before it
touched real recordings, and the hypotheses were fixed before the code
existed.

> **Research use only.** Not a medical device. The tool makes no clinical
> statements and is built to refuse them.

## Why

EEG summaries come from hand-built pipelines that give different answers
for the same data, or from general-purpose LLMs whose numbers nobody
checks. Three errors recur even when the code runs:

| error | what NeuroSignal does | evidence |
|---|---|---|
| a change in band power read as a change in an oscillation, when the 1/f exponent moved | reports peak power above the aperiodic fit next to band power, with the warning | H1: exponent alone moved 8-12 Hz band power by ≥ 30 % in 200/200 cases |
| volume conduction read as connectivity | reports debiased wPLI; PLV only as a contrast | H3: PLV > 0.3 in 92 % of pairs with no coupling at all; debiased wPLI 95th percentile 0.006-0.021 |
| a narrative that states values never computed, or a diagnosis | citation contract + mechanical claim checker; failed text is replaced and the failure shown | H4: 2157/2157 mutated explanations rejected, 60/60 faithful accepted |

## Quick start

```bash
make setup     # uv sync --frozen (Python 3.12)
make demo      # synthetic recording with known truth -> out/demo/report.html
uv run neurosignal report path/to/recording.edf --out out/rec
```

On a real recording: `make data` downloads a checksummed CHB-MIT subset
(about 650 MB) into `data/raw/chbmit/`; `chb01_03.edf` contains one seizure
(2996-3036 s in the database annotations).

**Windows (PowerShell).** `make` is not needed; every target is one `uv`
command (see the [Makefile](Makefile)):

```powershell
uv sync --frozen
uv run --frozen pytest
mkdir out -Force
uv run --frozen neurosignal synth --seed 42 --out out/demo.npz --duration 300 --events 2
uv run --frozen neurosignal report out/demo.npz --out out/demo
start out\demo\report.html
```

Reads EDF/EDF+, BDF, BrainVision (`.vhdr`) and a native `.npz`. Optional
LLM explanation (only the metrics are sent; the text is checked before it is
shown): `uv run --extra llm neurosignal report rec.edf --explainer llm`
with an Anthropic API key in the environment.

The report contains the explanation with hoverable citation chips, the
claim-check result, four figures (spectrum with aperiodic fit, per-channel
parameters, dwPLI vs PLV matrices, detector trace), and a table of every
parameter that touched the data.

## Results

Generated from result files with provenance: [VALIDATION_REPORT.md](docs/VALIDATION_REPORT.md).

| check | result |
|---|---|
| aperiodic exponent, 200 synthetic spectra | median error 0.014; agrees with specparam in 200/200 |
| alpha peak frequency | median error 0.067 Hz |
| bad-channel detection, 100 recordings | recall 1.00, precision 1.00 |
| claim checker (H4) | 2157/2157 live mutants caught across 9 operators |
| test suite | 17/17 code mutants killed |
| 1 h, 32 channels, 256 Hz, one core | 12.7 s, 1.5 GB peak memory |
| determinism | byte-identical `metrics.json` across processes (CI) |

Rejected hypotheses, reported as rejected ([FINDINGS.md](docs/FINDINGS.md)):

| hypothesis | result |
|---|---|
| H1 peak power stable within 0.05 log10 | 60.5 %: sampling noise of 3-minute recordings (method bias 0.001) |
| H2 synthetic event detection ≥ 0.90 at ≤ 2 false/h | 0.847 [0.803, 0.882] at 1.68/h on a benchmark with blinks, muscle, alpha/spindle bursts and event-free recordings |
| H3 plain wPLI ≤ 0.15 under the null at 2 min | 0.193 (passes at 10 min; the debiased estimator passes at both) |
| H5 CHB-MIT chb01, first detector | 2/7 seizures: the rhythm gate fell into the 1/f trap H1 describes |
| H6 held-out CHB-MIT chb03, frozen detector, one run | 4/7 seizures at 3.3 false/h; no false detection in seizure-free files |

The seizure detector is a deliberately simple, unsupervised baseline. Its
value here is the evidence trail: each change was forced by a measured
failure, chb01 became a development set once it had been used, and the
held-out test was committed before its data were downloaded.

## Engineering process

Problem → requirements → architecture → design → proof of concept → build →
validation → report, with a gate at each step; the git history shows the
order.

| document | contents |
|---|---|
| [TECHNICAL_REPORT](docs/TECHNICAL_REPORT.md) | the whole story with numbers: start here |
| [DESIGN_EVOLUTION](docs/DESIGN_EVOLUTION.md) | plan vs reality in chronological order: every turning point, its evidence, and what it guarantees |
| [STATISTICAL_FOUNDATIONS](docs/STATISTICAL_FOUNDATIONS.md) | eight probability models behind the decisions, each prediction checked against measurement |
| [PROBLEM_STATEMENT](docs/PROBLEM_STATEMENT.md) | evidence, existing tools, pre-registered hypotheses H1-H6 |
| [REQUIREMENTS](docs/REQUIREMENTS.md) | EARS requirements with IDs; a test fails CI if any lacks a test |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | components, boundaries, 12 ADRs |
| [DESIGN](docs/DESIGN.md) · [ICD](docs/ICD.md) | patterns, data model, every interface and file schema |
| [EQUATIONS](docs/EQUATIONS.md) | every method's maths and the alternative it beat |
| [DIAGRAMS](docs/DIAGRAMS.md) | signal chain, components, boundaries, sequences (Mermaid) |
| [DATA](docs/DATA.md) | CHB-MIT licence and checksums, ethics, synthetic generators |
| [THREAT_MODEL](docs/THREAT_MODEL.md) · [FMEA](docs/FMEA.md) | STRIDE threats; failure modes ranked by risk |
| [BUILD_JOURNAL](docs/BUILD_JOURNAL.md) | 11 dated issues: symptom, root cause, fix, lesson |
| [FINDINGS](docs/FINDINGS.md) | what validation changed |
| [VALIDATION_REPORT](docs/VALIDATION_REPORT.md) | generated evidence and SHA-256 manifest |
| [WORKFLOWS](docs/WORKFLOWS.md) | every command |

## Layout

    src/neurosignal/
      core/           Recording, Stage lifecycle, config, provenance, statistics
      io/             readers with refusals and de-identification
      synth/          ground-truth generators (spectra, discharges, artifacts, sources)
      preprocessing/  QC, zero-phase FIR filters, common average reference
      features/       Welch spectra, aperiodic fit, wPLI / dwPLI / PLV
      detection/      seizure-like event detector, event scoring
      explain/        template and LLM explainers, claim checker
      report/         figures, Markdown and HTML report
    validation/       campaign, detector tuning, explanation mutants, mutation testing, report
    results/          validation result files with provenance
    tests/            unit, property, metamorphic, differential, negative-control tests

## Reproduce everything

```bash
make check       # lint, strict types, tests
make data        # CHB-MIT subsets, verified against PhysioNet's SHA-256 list
make validate    # every result file, then docs/VALIDATION_REPORT.md
make mutation    # mutation testing of the test suite
```

## Data and citation

Real data: CHB-MIT Scalp EEG Database (PhysioNet, ODC-By 1.0); cite Shoeb
(2009) and Goldberger et al. (2000). Software citation: [CITATION.cff](CITATION.cff); archived on Zenodo,
[10.5281/zenodo.23447346](https://doi.org/10.5281/zenodo.23447346) (all versions).
Licence: MIT.
