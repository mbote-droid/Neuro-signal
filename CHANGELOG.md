# Changelog

All notable changes to this project. Format: Keep a Changelog; versions:
semantic versioning.

## [0.1.0] - 2026-10-12

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
- Deterministic explainer, optional Claude explainer, and a mechanical claim
  checker; self-contained HTML report with citation chips.
- Synthetic ground-truth generators; validation campaign; detector tuning;
  explanation mutants; test-suite mutation testing; generated validation
  report with SHA-256 manifest.
- Documentation set: problem statement with pre-registered hypotheses,
  requirements, architecture (ADRs), design, ICD, equations, diagrams, data,
  threat model, FMEA, workflows, build journal, findings, technical report.
