# Architecture

Phase 3. Components, boundaries and the decisions behind them. Diagrams are
in [DIAGRAMS.md](DIAGRAMS.md); interfaces in [ICD.md](ICD.md).

## 1. Components

```
src/neurosignal/
  core/           Recording value object, Stage lifecycle, registry, config, provenance, stats
  io/             readers (ports and adapters), de-identification, size limits
  synth/          ground-truth generators: EEG with known spectra, sources, artifacts, discharges
  preprocessing/  QC, FIR filters, re-referencing
  features/       Welch spectra, aperiodic/periodic fit, wPLI/PLV
  detection/      seizure-like event detector, event matching
  explain/        deterministic explainer, optional LLM explainer, claim checker
  report/         metrics assembly, figures, Markdown/HTML rendering
  pipeline.py     the composite: file -> metrics.json + report
  cli.py          `neurosignal` command
validation/       campaign experiments, mutation testing, report generator
```

Dependencies run one way:
`core <- io <- preprocessing <- features <- detection <- explain <- report <- pipeline <- cli`.
`synth` depends only on `core`. Nothing in the package imports `validation/`.

## 2. Boundaries

1. **Raw data is read-only.** The reader copies the signal into a new array;
   nothing is ever written next to the input file.
2. **Ground truth never reaches the method under test.** `synth` returns a
   `(Recording, GroundTruth)` pair; only the validation code and tests hold
   the `GroundTruth`. Detector thresholds are fixed in configuration, chosen
   on tuning seeds (ADR-008).
3. **The LLM sees numbers, not data.** The explainer's only input is the
   metrics dictionary, already de-identified (S-02, S-03). Its output is
   untrusted text until the claim checker accepts it.
4. **Offline only.** All filtering is zero-phase and therefore non-causal.
   A real-time path would be a separate, separately tested plugin (ADR-004).

## 3. Architecture decision records

### ADR-001 Pipes and filters with a Stage lifecycle, no workflow engine in the pipeline
Status: accepted
Context: per recording the work is a linear chain of six stages taking
seconds to minutes; nothing needs partial re-runs or caching of intermediates.
Decision: each stage is a `Stage` (Template Method: validate input, process,
check invariants, record parameters in the processing history). A
`Pipeline` composite runs them in order. The validation campaign is a set of
independent experiments driven by `make` targets.
Alternatives: Snakemake/Nextflow DAG (adds an engine and file-per-stage
intermediates for a chain with no branching; still a good fit if the
campaign grows past minutes); notebooks (hidden state); one monolithic
function (no per-stage invariants or parameter record).
Consequences: every parameter that reached the data is in
`metrics.json["processing"]`, which satisfies COBIDAS-style reporting.
Verification: `tests/test_pipeline.py` checks the processing history.

### ADR-002 Hexagonal readers with MNE as the adapter
Status: accepted
Context: EDF/EDF+, BDF and BrainVision parsers are mature in MNE; writing
our own would add attack surface and bugs.
Decision: a reader registry keyed by extension (`.edf`, `.bdf`, `.vhdr`,
`.npz`). Each adapter returns a `Recording`; the core never sees MNE objects.
Alternatives: pyEDFlib (EDF/BDF only); own parser (risk without benefit).
Consequences: MNE is a runtime dependency (about 40 MB). Swapping it means
changing one module.
Verification: `tests/test_io.py` round-trips EDF written by MNE.

### ADR-003 One `Recording` value object in microvolts
Status: accepted
Context: EDF stores physical units; MNE returns volts; a 10^6 slip is the
most common EEG unit error.
Decision: `Recording.data` is float64 µV, shape `(n_channels, n_samples)`;
the object is frozen; stages return new recordings.
Alternatives: a units library on every array (pint): heavy for one unit.
Consequences: amplitude thresholds in the config are in µV and checked by
tests against physiological ranges.
Verification: `tests/test_io.py::test_units_are_microvolts`.

### ADR-004 Zero-phase FIR for offline analysis
Status: accepted
Context: spectra, coupling and event timing are all computed offline.
Decision: linear-phase FIR (Hamming window, length from the transition
width) applied forward and backward, i.e. zero phase.
Alternatives: IIR Butterworth (non-linear phase unless applied
forward-backward, and forward-backward squares the magnitude response with
less control of the transition band); causal FIR (group delay of
`(N-1)/2fs`, about 0.85 s for the 0.5 Hz high-pass, would shift event
onsets).
Consequences: the pipeline is non-causal and must never be reused for
real-time work without a separate causal plugin.
Verification: `tests/test_filters.py` (impulse not shifted; ripple and
attenuation within spec).

### ADR-005 Common average reference only for referential montages
Status: accepted
Context: CHB-MIT (the real-data set) is a bipolar double-banana montage.
Averaging bipolar derivations has no physical meaning.
Decision: detect bipolar channel names (`A-B`); apply CAR only when the
montage is referential, excluding bad channels from the average.
Alternatives: always CAR (wrong for bipolar); never CAR (leaves the
reference electrode's activity in every channel of referential data).
Consequences: CAR lowers rank by one; noted for any future ICA stage.
Verification: `tests/test_reference.py`.

### ADR-006 Own aperiodic fitter, specparam as the differential oracle
Status: accepted
Context: specparam 2.0 is a release candidate at the time of writing; its
API has changed between versions. The fit is about 150 lines.
Decision: implement the fixed-mode model (no knee) with robust aperiodic
initialisation and greedy Gaussian peak search, following Donoghue et al.
(2020); use specparam in tests as an independent implementation.
Alternatives: depend on specparam at runtime (API churn, extra dependency
in the report path); IRASA (no peak parameters).
Consequences: our fitter must be validated on ground truth (V-01, V-02) and
against specparam (V-03).
Verification: `validation/campaign.py aperiodic`.

### ADR-007 wPLI as the reported coupling measure, PLV only as a contrast
Status: accepted
Context: sensor-space EEG mixes sources instantaneously (H3).
Decision: report alpha-band wPLI matrices; report PLV alongside only to
show the inflation.
Alternatives: coherence, PLV (inflated by zero-lag mixing); imaginary
coherency (amplitude-weighted, noisier than wPLI); source-space
connectivity (needs a head model, out of scope).
Verification: `validation/campaign.py connectivity`.

### ADR-008 Unsupervised line-length detector, thresholds from synthetic tuning seeds
Status: accepted
Context: no labelled training data may be used without leakage risk, and
the evaluation must be honest about transfer to real data (H5).
Decision: line length in 2 s windows (1 s step), robust z-score against the
recording's own baseline, a multi-channel vote and a minimum duration.
Thresholds are chosen once on synthetic tuning seeds (0-99) and evaluated on
disjoint seeds (1000+) and on CHB-MIT, never re-tuned on the latter.
Alternatives: supervised classifier on CHB-MIT (needs patient-grouped
cross-validation and more data than chb01; a later project); band-power
ratio detector (sensitive to aperiodic shifts, see H1).
Verification: `tests/test_detection.py`, `validation/campaign.py detection`.

### ADR-009 Citation contract and a mechanical claim checker for explanations
Status: accepted
Context: the backlog requires one LLM step that explains computed metrics
with every claim linked to a value; no vision model reading plots.
Decision: explanations must write `value [[metric.key]]` for every number.
A deterministic checker (regular expressions, no model) verifies keys,
values at the written precision, channel names, diagnostic language and the
research-use notice. A template explainer is the default; the LLM explainer
is optional and its output is accepted only if the checker passes.
Alternatives: LLM-as-judge (a second unverified model); free text with no
contract (unverifiable).
Consequences: the checker is a sensor and is itself mutation-tested (H4).
Verification: `validation/campaign.py checker`.

### ADR-010 Determinism by construction
Status: accepted
Decision: `metrics.json` has sorted keys, floats rounded to 6 significant
digits and no wall-clock values; timing goes to a separate `run.json`.
Seeds expand through `numpy.random.SeedSequence`; BLAS runs single-threaded
in CI.
Verification: CI job runs the report twice and compares bytes (R-01).

### ADR-011 A command-line tool, not a service
Status: accepted
Context: single user, research data, 8 GB laptop.
Decision: a CLI and a self-contained HTML report.
Alternatives rejected: web service or microservices (would need upload
handling, authentication, retention policy; no stated requirement), event
sourcing, CQRS, Kubernetes.
Consequences: "drop a file" means `neurosignal report FILE`. A hosted
service would need the threat model extended (rate limits, ephemeral
storage) before it is built.

### ADR-012 Whole-recording arrays, channel-wise filtering
Status: accepted
Context: 8 GB target machine. A 1-hour, 64-channel, 512 Hz recording is
118 M samples, 0.94 GB in float64.
Decision: load the recording once; filter one channel at a time; compute
features in windows. No overlap-save chunking.
Alternatives: chunked overlap-save streaming (more code, edge handling
at chunk boundaries; not needed below about 4 GB of signal).
Consequences: memory is about 2-3 times the signal size; recordings above
the 2 GB file limit are refused (S-01).
Verification: `validation/campaign.py resources` (P-01).
