# Changelog

All notable changes to this project. Format: Keep a Changelog; versions:
semantic versioning.

## [Unreleased]

### Added
- Gemini and local Ollama backends for the LLM explainer
  (`--explainer gemini|ollama`, `--model`), over plain HTTP with no new
  dependency; keys from the environment, sent in headers only (ADR-013).
- Fuzz tests for the checker and readers; four H4 operators (3334/3334);
  five test-suite mutants (23/23); synthetic adversarial artifacts and an
  exploratory experiment (chewing: 6.0 false detections per hour).
- Pre-registered hypothesis H7 (PROBLEM_STATEMENT §10) and its harness,
  `validation/llm_eval.py`: resumable runs that never repeat a model call,
  a blinded audit sheet and scoring; results go into the validation report.

### Fixed
- Bug hunt (BUILD_JOURNAL ISSUE-013 to 021): the checker rejects invisible
  characters, reads leading-dot numbers and signs after markup, survives huge
  exponents, and masks the recording's channel names; damaged files are
  refused instead of crashing; .npz decompression bombs are refused; flat
  edges are no longer measured twice; one ECG channel no longer overturns the
  montage decision and non-EEG channels are left out of the average; the LLM
  fallback survives missing packages, SDK errors and non-JSON replies;
  recordings under 10 s are refused; report.md escapes HTML.
- The claim checker missed sign flips written with a typographic minus or
  en dash (issue #21, reported by neowalter); a range dash after a citation
  no longer reads as a minus; scientific notation reads as one number. New
  mutation operator `typographic_minus` (H4: 2386/2386). H7 keeps the
  registered checker and reports the corrected one as a secondary analysis.

## [0.1.1] - 2026-10-18

### Fixed
- Text files are checked out with LF line endings on every platform
  (`.gitattributes`), so the SHA-256 result manifest also verifies on Windows.
- Explanation wording: singular/plural counts, a clearer line-noise sentence,
  no "-0.000", an explicit note that zero detected events is not evidence of
  absence, and a disclaimer that no longer calls the software "validated".
  The H4 checker campaign was re-run on the new text (2157/2157).

### Changed
- CITATION.cff title: "validation-first" instead of "validated" (four of
  six pre-registered hypotheses were rejected).
- README: Windows (PowerShell) commands; how to get a real recording.

## [0.1.0] - 2026-10-18

Archived on Zenodo: [10.5281/zenodo.23447347](https://doi.org/10.5281/zenodo.23447347).

### Added
- `neurosignal` CLI: `report`, `synth`, `explain`, `check`, `info`.
- Readers for EDF/EDF+, BDF, BrainVision and native `.npz`, with size and
  extension refusal, µV units, header de-identification and duplicate-channel
  cleanup.
- Quality control (flat, noisy, low channels; line-noise ratio), zero-phase
  FIR notch and band-pass, common average reference for referential montages.
- Welch spectra outside detected events, aperiodic/periodic parameterisation,
  alpha peak and band power, PLV / wPLI / debiased wPLI coupling.
- Rhythmic seizure-like event detector (1-20 Hz line length, robust z, channel
  vote, background-normalised rhythm gate) with thresholds chosen on synthetic
  data only.
- Deterministic explainer, optional LLM explainer, and a mechanical claim
  checker; self-contained HTML report with citation chips.
- Synthetic ground-truth generators; validation campaign; detector tuning;
  explanation mutants; test-suite mutation testing; generated validation
  report with SHA-256 manifest.
- Documentation set: problem statement with pre-registered hypotheses,
  requirements, architecture (ADRs), design, ICD, equations, diagrams, data,
  threat model, FMEA, workflows, build journal, findings, technical report.
