# Changelog

All notable changes to this project. Format: Keep a Changelog; versions:
semantic versioning.

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
