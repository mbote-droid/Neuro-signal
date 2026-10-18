# Requirements

Phase 2. Requirements are written in EARS form. Prefixes: **F** functional,
**V** validity, **P** performance, **S** security and privacy, **R**
reproducibility. Verification methods: **T** test, **A** analysis
(validation campaign), **I** inspection, **D** demonstration.

`tests/test_traceability.py` fails CI if any ID below is not named in at
least one test file, so this table cannot silently drift from the tests.

## Functional

| ID | requirement | rationale | design element | verif. |
|---|---|---|---|---|
| F-01 | The reader shall load EDF/EDF+, BDF, BrainVision and native `.npz` files into a `Recording` whose data are float64 microvolts, shape `(n_channels, n_samples)`. | one data model; µV vs V slips become impossible downstream | `io.readers`, `core.recording` | T |
| F-02 | If a file's extension is not registered, then the reader shall refuse it without parsing. | parsers are an attack surface; no content sniffing | `io.readers.read` | T |
| F-03 | When a channel stays within ±0.1 µV of a constant for more than 5 s, the pipeline shall mark the channel bad (`flat`). | disconnected electrodes give flat lines that bias the average reference | `preprocessing.qc` | T |
| F-04 | When a channel's robust amplitude (MAD) exceeds 5 times the median MAD over channels, or falls below 0.2 times it, the pipeline shall mark the channel bad (`noisy` / `low`). | bridged or loose electrodes | `preprocessing.qc` | T |
| F-05 | The pipeline shall measure the line-noise ratio (power in ±1 Hz around mains over power in 1-45 Hz) on every channel before and after cleaning. | mains is 50 Hz in Kenya; residual line noise must be reported, not assumed away | `preprocessing.qc.line_noise_ratio` | T |
| F-06 | The pipeline shall apply a zero-phase FIR notch at the mains frequency and its harmonics below Nyquist, then a zero-phase FIR band-pass (default 0.5-45 Hz). | offline analysis: no phase distortion (EQUATIONS §2) | `preprocessing.filters` | T |
| F-07 | When the montage is referential, the pipeline shall re-reference to the common average of good channels; when it is bipolar, the pipeline shall keep the montage. | CAR of bipolar derivations has no physical meaning | `preprocessing.reference` | T |
| F-08 | The pipeline shall estimate each channel's power spectrum by Welch's method with 2 s Hann windows and 50 % overlap. | 0.5 Hz resolution, variance reduced by segment averaging (EQUATIONS §4) | `features.spectral` | T |
| F-09 | The pipeline shall fit each spectrum, over 2-40 Hz, with an aperiodic component and Gaussian peaks, reporting offset, exponent, peaks, R² and error. | separates oscillations from 1/f activity (EQUATIONS §5) | `features.aperiodic` | T |
| F-10 | The pipeline shall report, per channel and averaged, the dominant alpha peak (7-14 Hz) frequency and its power above the aperiodic fit, and the canonical 8-12 Hz band power. | the H1 comparison, shown in every report | `features.spectral`, `features.aperiodic` | T |
| F-11 | The pipeline shall compute alpha-band (8-12 Hz) wPLI and PLV for every pair of good channels. | coupling, with the volume-conduction-robust measure as primary (EQUATIONS §6) | `features.connectivity` | T |
| F-12 | The pipeline shall detect rhythmic seizure-like events and report onset, offset, duration and the channels involved. | the event question in every review | `detection.seizure` | T |
| F-13 | The pipeline shall write `metrics.json`, `report.md`, `report.html` and figures to the output directory. | one command, one self-contained result | `report` | T, D |
| F-14 | The deterministic explainer shall attach a `[[metric.key]]` citation to every number it writes. | explanation contract (ADR-009) | `explain.template` | T |
| F-15 | Where an API key is available, the LLM explainer shall produce text under the same citation contract; where it is not, the CLI shall fall back to the deterministic explainer and say so. | optional, never required | `explain.llm` | T |
| F-16 | The claim checker shall reject an explanation that cites an unknown key, states a number that does not match its cited metric at the written precision, states an uncited number, names a channel absent from the recording, uses diagnostic language, or lacks the research-use-only notice. | the faithfulness sensor (H4) | `explain.checker` | T, A |
| F-17 | The CLI shall provide `report`, `synth`, `explain`, `check` and `info` commands. | every workflow is one command | `cli` | T |

## Validity

| ID | requirement | threshold | verif. |
|---|---|---|---|
| V-01 | On synthetic spectra with known parameters, the aperiodic exponent shall be recovered within a median absolute error of 0.1. | n >= 200 spectra | A, T |
| V-02 | On the same spectra, the alpha peak frequency shall be recovered within a median absolute error of 0.5 Hz. | n >= 200 | A, T |
| V-03 | The aperiodic fitter shall agree with specparam (independent implementation) on the exponent within 0.1 in at least 90 % of synthetic spectra. | differential test | A, T |
| V-04 | Injected flat and noisy channels shall be detected with recall and precision of at least 0.95. | n >= 100 recordings | A, T |
| V-05 | The band-pass filter shall have passband ripple <= 0.1 dB and stopband attenuation >= 40 dB, and shall not shift an impulse (zero phase). | design spec | T |
| V-06 | Hypothesis H2 (event detection, synthetic) | PROBLEM_STATEMENT §4 | A |
| V-07 | Hypothesis H3 (volume conduction) | PROBLEM_STATEMENT §4 | A, T |
| V-08 | Hypothesis H4 (claim checker) | PROBLEM_STATEMENT §4 | A, T |
| V-09 | Hypotheses H1, H5 and H6 are evaluated and reported, accepted or rejected. | PROBLEM_STATEMENT §4, §9 | A |
| V-10 | Detector thresholds shall be chosen on tuning seeds disjoint from the evaluation seeds, and never on CHB-MIT. | no double dipping | I, T |

## Performance

| ID | requirement | verif. |
|---|---|---|
| P-01 | A 1-hour, 32-channel, 256 Hz recording shall be processed in at most 5 minutes on one CPU core with peak resident memory at most 2 GB. | A |

## Security and privacy

| ID | requirement | verif. |
|---|---|---|
| S-01 | If a file exceeds the size limit (default 2 GB), then the reader shall refuse it before parsing. | T |
| S-02 | The reader shall drop patient name, birth date, sex, hand and measurement date from the header; no output file shall contain them. | T |
| S-03 | The LLM explainer shall receive only the metrics dictionary: no raw signal and no header fields. | T, I |
| S-04 | The API key shall be read from the environment only and never written to any output or log. | T, I |
| S-05 | If a `.npz` file contains object arrays, then the reader shall refuse it (no pickle loading). | T |

## Reproducibility

| ID | requirement | verif. |
|---|---|---|
| R-01 | Processing the same file with the same configuration shall produce a byte-identical `metrics.json` in separate processes. | T (CI job) |
| R-02 | Every `metrics.json` shall carry provenance: package version, git commit and dirty flag, dependency versions, input SHA-256, full configuration and seed. | T |
| R-03 | The synthetic generator shall produce identical data for the same seed in separate processes. | T |
| R-04 | Every validation result file shall carry provenance and be listed with its SHA-256 in the manifest. | A |

## Traceability matrix

| ID | design element | test file | result file |
|---|---|---|---|
| F-01, F-02, S-01, S-02, S-05 | `io/readers.py`, `io/deid.py` | `tests/test_io.py` | n/a |
| F-03, F-04, F-05, V-04 | `preprocessing/qc.py` | `tests/test_qc.py` | `results/validation/qc.json` |
| F-06, V-05 | `preprocessing/filters.py` | `tests/test_filters.py` | n/a |
| F-07 | `preprocessing/reference.py` | `tests/test_reference.py` | n/a |
| F-08, F-10 | `features/spectral.py` | `tests/test_spectral.py` | `results/validation/aperiodic.json` |
| F-09, V-01, V-02, V-03 | `features/aperiodic.py` | `tests/test_aperiodic.py` | `results/validation/aperiodic.json` |
| F-11, V-07 | `features/connectivity.py` | `tests/test_connectivity.py` | `results/validation/connectivity.json` |
| F-12, V-06, V-10 | `detection/seizure.py`, `detection/events.py` | `tests/test_detection.py` | `results/validation/detection_synthetic.json` |
| V-09 | `validation/campaign.py` | `tests/test_campaign.py` | `results/validation/h1_confound.json`, `chbmit_h5_registered.json`, `chbmit_heldout.json` |
| F-13, R-01, R-02 | `pipeline.py`, `report/` | `tests/test_pipeline.py` | n/a |
| F-14, F-15, F-16, V-08, S-03, S-04 | `explain/` | `tests/test_explain.py` | `results/validation/checker.json` |
| F-17 | `cli.py` | `tests/test_cli.py` | n/a |
| R-03 | `synth/eeg.py` | `tests/test_synth.py` | n/a |
| P-01, R-04 | `validation/` | `tests/test_campaign.py` | `results/validation/resources.json`, `results/validation/MANIFEST.sha256` |
