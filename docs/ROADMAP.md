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
| Gemini run (30 recordings, over several days of free quota): 30/30 accepted, 24 first time; H7a accepted | ✅ 2026-10-25 | `results/validation/llm_eval_gemini.json` |
| Local Ollama run (30 recordings): 0/30 accepted | ✅ 2026-10-25 | `results/validation/llm_eval_ollama.json` |
| Secondary analysis with the corrected checker (`recheck`): no typographic signs, no verdict changes | ✅ 2026-10-25 | `results/validation/llm_recheck.json` |
| Blinded audit of accepted explanations (H7c): 3/20 misleading, H7c rejected | ✅ 2026-10-27 | `results/validation/llm_audit.json` |

## Maintenance and outside reports

| item | status | evidence |
|---|---|---|
| Issue #21: sign flips written with a typographic minus passed the checker; fixed, new mutation operator, H4 re-run (2386/2386) | ✅ 2026-10-22 | BUILD_JOURNAL ISSUE-012 |

## Bug hunt (after H7, before preprint v2)

Issue #21 showed that the tests only catch the errors their authors
imagined. A systematic search, before the paper's claims are frozen; every
finding becomes a test and a BUILD_JOURNAL entry.

| item | status | notes |
|---|---|---|
| Fuzz the claim checker: random Unicode, number formats, citation placement | ✅ 2026-10-26 | three bypasses fixed (ISSUE-013); a decimal comma still reads as two numbers (rejects correct text, safe) |
| Fuzz the file readers: corrupted, truncated and unusual files | ✅ 2026-10-26 | damaged files refused cleanly; .npz bombs refused (ISSUE-014, 018) |
| Edge-case recordings through the whole pipeline | ✅ 2026-10-26 | short recordings refused; channel-name and NaN handling fixed (ISSUE-015, 020) |
| Structured correctness and security review of the code | ✅ 2026-10-26 | independent review: 11 findings, 10 fixed, 1 documented (coupling memory) |
| Second look at the mutation sets | ✅ 2026-10-26 | H4: four operators, 3334/3334; test suite: five mutants, 23/23 |
| Adversarial artifacts for the detector | ✅ 2026-10-26 | exploratory: chewing 6.0 false/h vs 2.4 baseline (ISSUE-021) |

## Publication

| item | status | notes |
|---|---|---|
| Fold H7a, H7b and the bug hunt into FINDINGS (F-11), the technical report and preprint v2 | ✅ 2026-10-27 | `paper/preprint.md`; H7c placeholders marked `H7C-PENDING` |
| Audit reading guide | ✅ 2026-10-27 | `results/validation/llm_eval/audit_guide.md` |
| Journal package drafts: highlights, structured abstract, cover letter, checklist | ✅ 2026-10-27 | `paper/jnm/` |
| Fill H7c into the paper, FINDINGS F-11, the technical report and the journal package | ✅ 2026-10-27 | `paper/preprint.md` §3.7 |
| Acknowledge the outside report (#21) once the reporter says how to be named | ⏭ | |
| Release v0.1.2 (H7 and the bug hunt), archived on Zenodo | 🔄 | `CHANGELOG.md` |
| Post preprint v2 (Zenodo new version; one other preprint server optional) | ⏭ | |
| Submit to Journal of Neuroscience Methods | ⏭ | ends active work on the 0.1 line |
| Respond to reviewers | 💤 | weeks to months after submission |
| JOSS software paper | 💤 | once others use the tool |

## After the journal submission

| item | status | notes |
|---|---|---|
| Idea 3: a local model writes realistic, subtly wrong explanations to measure the checker's semantic blind spot (FINDINGS F-4) | 💤 | reuses the H7 harness; may also answer reviewers |
| An AI judge tested, not trusted: give the H7 explanations to an LLM judge (single, or an optimist-versus-sceptic debate) and measure its agreement with the blinded H7c audit | 💤 | asks whether a judge catches the semantic errors the checker cannot; the human audit is the ground truth |
| Idea 1: an offline small model plus a mechanical verifier for lab-result summaries in low-connectivity clinics | 💤 | a follow-on project in its own repository, reusing this method |

## Version 0.2 research (one pull request each)

| item | status | notes |
|---|---|---|
| Spatial cue (frontal, symmetric) to separate blinks from slow ictal delta, then lower the rhythm-gate floor | 💤 | FINDINGS F-7 |
| Detector with hidden states (HSMM fitted by EM) compared with the threshold detector | 💤 | |
| Spectral fit aware of excluded event windows | 💤 | |
| Leave non-EEG channels (ECG, VNS) out of spectra, coupling and the detector's channel vote | 💤 | ISSUE-017; needed before more CHB-MIT subjects |
| EMG cue against chewing (20-60 Hz power locked to the rhythm) | 💤 | ISSUE-021, FINDINGS F-10 |
| Absolute amplitude plausibility and clipping detection | 💤 | ISSUE-014 |
| Section-scoped citation rules: each report section may cite only its own metrics, with short descriptions the model must not contradict | 💤 | the error H7c found (FINDINGS F-11); a new explainer version needs a new registration |
| Coupling memory linear in the channel count | 💤 | about 2.5 GB at 128 channels today |
| Confirmatory test sized by the power analysis (about 76 seizures), pre-registered on OSF | 💤 | STATISTICAL_FOUNDATIONS §7 |
