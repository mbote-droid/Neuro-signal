# Design

Phase 4. Patterns, data model and module responsibilities. Interfaces are
frozen in [ICD.md](ICD.md); the maths behind each method is in
[EQUATIONS.md](EQUATIONS.md).

## 1. Data model

```
Recording (frozen)
  data          (n_channels, n_samples) float64, µV, read-only array
  sfreq         Hz
  channels      tuple[str]           unique
  annotations   tuple[Annotation]    onset_s, duration_s, description
  bad_channels  tuple[str]           subset of channels
  source_sha256 str                  SHA-256 of the input file
  subject_id    str                  "rec-<12 hex of sha256>": pseudonymous
  history       tuple[dict]          one entry per stage: name + every parameter
```

No bare arrays cross a module boundary: stages take and return a
`Recording`; feature functions take a `Recording` and return a typed result
(`Spectrum`, `AperiodicFit`, `Connectivity`, `DetectedEvent`). Units are in
names and docstrings (`_hz`, `_s`, `_uv`, `_uv2`).

## 2. Patterns and where they are used

| pattern | where | why |
|---|---|---|
| Value Object | `Recording`, `PipelineConfig`, `Interval`, all result dataclasses | frozen; impossible to change data behind a stage's back |
| Template Method | `core.stage.Stage.__call__`: validate, process, check invariants, record parameters | every stage gets the same NaN check, sample-count invariant and parameter record for free |
| Composite | `core.stage.Pipeline` | a chain of stages is itself a stage |
| Null Object | `core.stage.Identity` | ablations without `if` branches |
| Registry / Factory | `io.readers.READERS` keyed by extension | add a format without touching the core |
| Adapter | MNE readers behind `READERS` | MNE objects never leave `io/` |
| Strategy | `DetectorParams` (window, thresholds, bands, gate); explainer choice (`template` / `llm`) | swap a method by configuration |
| Builder | `PipelineConfig.from_toml` validates every key before anything runs | a typo cannot silently keep a default |
| Decorator-like provenance | `Recording.evolve(step=...)` appends parameters at every stage | processing history without logging code in algorithms |

Rejected: inheritance trees of filter or detector classes (one function
each is enough), dependency-injection frameworks, a plugin entry-point
system (one package, one user).

## 3. Module responsibilities

| module | responsibility | must not |
|---|---|---|
| `core/recording.py` | data model and its invariants | know about files or methods |
| `core/config.py` | every tunable number, validated | contain logic |
| `core/stage.py` | stage lifecycle | contain signal processing |
| `core/provenance.py` | git, versions, hashes, no wall-clock time | influence results |
| `core/stats.py` | Wilson, rule of three, Poisson bound, BH | |
| `io/readers.py` | size/extension refusal, adapters, µV, duplicate-channel cleanup, pseudonymous id | let header identity fields through |
| `synth/eeg.py` | ground-truth generators | be imported by the pipeline |
| `preprocessing/` | flat/amplitude QC, FIR filters, CAR | use future samples outside zero-phase filtering |
| `features/` | Welch, aperiodic fit, wPLI/dwPLI/PLV | see ground truth |
| `detection/` | detector, event scoring | be tuned on real data |
| `explain/` | template, LLM, checker | pass unchecked text to a report without the check result next to it |
| `report/` | metrics files, figures, Markdown, HTML | edit numbers |
| `pipeline.py` | orchestration and the metrics dictionary | |
| `cli.py` | argument parsing, exit codes | contain analysis logic |

Dependency direction: `core <- io <- preprocessing <- features <- detection <- pipeline <- explain <- report <- cli`
(`explain.checker` imports `pipeline.flatten` only).

## 4. Stage order and why

1. **read**: extension and size refused first, then MNE parses.
2. **qc_flat** on raw data: a filter would make a flat line ring and hide it.
3. **filter**: notch then band-pass, zero phase, one channel at a time.
4. **qc_amplitude** on filtered data: slow drift would otherwise inflate the MAD.
5. **reference**: CAR of good channels, referential montages only.
6. **detect events** (1-20 Hz line length + rhythm gate).
7. **spectra and coupling outside the events**, so they describe the background.
8. **metrics**, then **explain**, then **check**, then **render**.

## 5. Coding rules

- `ruff` (max complexity 10) and `mypy --strict` on `src/` in CI.
- Numerics are pure functions; I/O only in `io/`, `report/`, `cli.py`.
- Every tunable number lives in `PipelineConfig` or `DetectorParams`.
- Docstrings state units and shapes.
- Floats in `metrics.json` are rounded to 6 significant digits; keys sorted.

## 6. What a user sees

`neurosignal report FILE --out DIR` writes `report.html` (self-contained,
light and dark themes, banner "research use only", explanation with
citation chips whose tooltip shows the cited key and value, claim-check
status, four figures, the full processing table), `report.md`,
`metrics.json`, `explanation.md` and `run.json` (timings, kept out of
`metrics.json` so the latter stays byte-identical).
