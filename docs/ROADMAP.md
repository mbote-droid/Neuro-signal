# Roadmap

What has been built, what is in progress, and what comes next. Updated in
the same pull request that completes an item, so this file always matches
the repository. Dates are when an item was merged.

Status: ✅ done · 🔄 in progress · ⏭ next · 💤 later

## Release 0.1: the validated pipeline

| item | status | evidence |
|---|---|---|
| Problem statement with pre-registered hypotheses H1-H6 | ✅ 2026-10-12 | [PROBLEM_STATEMENT.md](PROBLEM_STATEMENT.md) |
| Pipeline: readers, QC, filters, spectra, aperiodic fit, dwPLI, detector, report, CLI | ✅ 2026-10-12 | `src/neurosignal/` |
| Validation campaign, CHB-MIT development and held-out tests, mutation testing | ✅ 2026-10-12 | [VALIDATION_REPORT.md](VALIDATION_REPORT.md) |
| Design evolution and statistical foundations | ✅ 2026-10-18 | [DESIGN_EVOLUTION.md](DESIGN_EVOLUTION.md), [STATISTICAL_FOUNDATIONS.md](STATISTICAL_FOUNDATIONS.md) |
| Windows support (line endings, PowerShell instructions) | ✅ 2026-10-18 | README |
| Releases v0.1.0 and v0.1.1 on Zenodo | ✅ 2026-10-18 | [10.5281/zenodo.23447346](https://doi.org/10.5281/zenodo.23447346) |
| Methods preprint | ✅ 2026-10-18 | [10.5281/zenodo.23448015](https://doi.org/10.5281/zenodo.23448015) |

## LLM explainer evaluation (H7)

| item | status | evidence |
|---|---|---|
| H7 pre-registered before any model call | ✅ 2026-10-18 | [PROBLEM_STATEMENT.md](PROBLEM_STATEMENT.md) §10 |
| Gemini and local Ollama backends; evaluation harness | ✅ 2026-10-18 | ADR-013, `validation/llm_eval.py` |
| Models recorded before the run (`gemini-3.8-flash`, `qwen2.5:3b`) | ✅ 2026-10-21 | PROBLEM_STATEMENT §10 |
| Gemini run (30 recordings, over several days of free quota) | 🔄 | `results/validation/llm_eval_gemini.json` |
| Local Ollama run (30 recordings) | 🔄 | `results/validation/llm_eval_ollama.json` |
| Blinded audit of accepted explanations (H7c) | ⏭ | `results/validation/llm_audit.json` |
| Secondary analysis with the corrected checker (`recheck`) | ⏭ | `results/validation/llm_recheck.json` |

## Maintenance and outside reports

| item | status | evidence |
|---|---|---|
| Issue #21: sign flips written with a typographic minus passed the checker; fixed, new mutation operator, H4 re-run (2386/2386) | ✅ 2026-10-22 | BUILD_JOURNAL ISSUE-012 |

## Publication

| item | status | notes |
|---|---|---|
| Fold H7 into FINDINGS, the technical report and preprint v2 | ⏭ | after the runs and the audit |
| Post preprint v2 (Zenodo new version; one other preprint server optional) | ⏭ | |
| Submit to Journal of Neuroscience Methods | ⏭ | ends active work on the 0.1 line |
| Respond to reviewers | 💤 | weeks to months after submission |
| JOSS software paper | 💤 | once others use the tool |

## After the journal submission

| item | status | notes |
|---|---|---|
| Idea 3: a local model writes realistic, subtly wrong explanations to measure the checker's semantic blind spot (FINDINGS F-4) | 💤 | reuses the H7 harness; may also answer reviewers |
| Idea 1: an offline small model plus a mechanical verifier for lab-result summaries in low-connectivity clinics | 💤 | a follow-on project in its own repository, reusing this method |

## Version 0.2 research (one pull request each)

| item | status | notes |
|---|---|---|
| Spatial cue (frontal, symmetric) to separate blinks from slow ictal delta, then lower the rhythm-gate floor | 💤 | FINDINGS F-7 |
| Detector with hidden states (HSMM fitted by EM) compared with the threshold detector | 💤 | |
| Spectral fit aware of excluded event windows | 💤 | |
| Confirmatory test sized by the power analysis (about 76 seizures), pre-registered on OSF | 💤 | STATISTICAL_FOUNDATIONS §7 |
