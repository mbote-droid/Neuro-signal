# NeuroSignal: technical report

*Samuel Ngigi Mbote. Version 0.1.2, 2026-10-28.*

## 1. Abstract

NeuroSignal turns one scalp EEG file into a report: channel quality, a
spectrum split into aperiodic and oscillatory parts, phase coupling that
ignores volume conduction, candidate rhythmic seizure-like events, and a
plain-language explanation in which every number is mechanically traced to
a computed value. Every method was checked against synthetic ground truth
before touching real data, and six hypotheses were fixed before building.
The spectral fit recovers the aperiodic exponent with a median error of
0.014 and agrees with specparam in 200 of 200 spectra; bad-channel detection
had perfect recall and precision on 100 recordings; the claim checker
rejected 3334 of 3334 live mutated explanations after a rounding-tie defect
found on its first run was fixed. Four hypotheses were rejected and are
reported as such: canonical band power moved by at least 30 % in every case
where only the 1/f exponent changed, but fitted peak power was too noisy
across separate 3-minute recordings to meet the registered bound (H1); plain
wPLI was biased at 2 minutes (H3, the debiased estimator passed); the event
detector reached sensitivity 0.85 at 1.7 false detections per hour on a
realistic synthetic benchmark (H2), and on a held-out CHB-MIT subject found
4 of 7 seizures at 3.3 false detections per hour (H6). Under a citation
contract checked by rule, a cloud language model wrote acceptable
explanations for 30 of 30 recordings and a small local model for none, its
faulty text never reaching a report (H7). A 1-hour,
32-channel recording is processed in 13 s with 1.5 GB peak memory on one
core.

## 2. Problem and hypotheses

EEG summaries are produced by hand-built pipelines that differ silently
(Trübutschek et al. 2024; Robbins et al. 2020) or by general LLMs whose
numbers nobody checks. Three errors recur even when code runs: band power
read as oscillation when the 1/f exponent moved (Donoghue et al. 2020),
volume conduction read as connectivity (Nolte et al. 2004; Vinck et al.
2011), and narrative text stating values that were never computed.
Hypotheses H1-H5 were committed before any code; H6 was committed before
its data were downloaded ([PROBLEM_STATEMENT.md](PROBLEM_STATEMENT.md)).

## 3. System overview

A command-line tool (`neurosignal report FILE`) runs a fixed chain of
stages, each recording its parameters: reader (size and extension refused
first, µV, no identity fields), flat-channel QC on raw data, zero-phase FIR
notch and 0.5-45 Hz band-pass, amplitude QC, common average reference for
referential montages, event detection, then spectra and coupling on the
data outside events. `metrics.json` is byte-identical across runs; the
explainer (deterministic template, or optionally an LLM given only the
metrics) writes `value [[metric.key]]` for every number, and a checker with
no model in it verifies every citation. Ground truth never reaches the
methods. Architecture and its twelve decision records:
[ARCHITECTURE.md](ARCHITECTURE.md); diagrams: [DIAGRAMS.md](DIAGRAMS.md).

## 4. Methods and why each was chosen

Full mathematics and rejected alternatives: [EQUATIONS.md](EQUATIONS.md).

| stage | method | why, in one line |
|---|---|---|
| filtering | Hamming-window FIR, single pass with delay compensation (zero phase, magnitude H, not H²) | offline timing must not shift; a causal 0.5 Hz high-pass would delay events by 3.3 s |
| line noise | 50 Hz FIR notch plus harmonics; residual ratio measured before and after | Kenyan mains; residual is reported, not assumed |
| reference | common average of good channels, referential montages only | averaging bipolar derivations (CHB-MIT) is meaningless |
| spectra | Welch, 2 s Hann, 50 % overlap; event windows excluded | 0.5 Hz resolution; a discharge in the window bent the background fit |
| aperiodic | own specparam-style fit (robust line, greedy Gaussian peaks, joint least squares), specparam as test oracle | separates oscillations from 1/f; no runtime dependency on a release candidate |
| coupling | debiased wPLI² (reported), PLV (contrast) | zero-lag mixing inflates PLV; plain wPLI is biased with few epochs |
| events | 1-20 Hz line length, robust z, channel vote, minimum duration, fundamental-frequency gate on the background-normalised spectrum; thresholds from synthetic tuning seeds only | cheap, unsupervised, and every component was forced by a measured failure |
| explanation | citation contract + regular-expression checker | an unverified second model cannot validate the first |

## 5. Validation method

Unit, property-based (linearity, time-shift equivariance), metamorphic
(Parseval), numerical (filter response, impulse position), differential
(specparam) and ground-truth tests; negative controls (causal filter, PLV
under volume conduction, detector without its rhythm gate); a determinism
job; resource budget; mutation testing of the explanation checker (nine
operators, equivalence decided independently of the checker) and of the
test suite (23 code mutants), fuzzing of the checker and the readers. Intervals: Wilson for proportions,
rule of three for zero failures, a Wilson-Hilferty Poisson bound for
false-detection rates. Seed sets are disjoint between tuning and
evaluation. Evidence: [VALIDATION_REPORT.md](VALIDATION_REPORT.md), generated
from result files with provenance and a SHA-256 manifest.

## 6. Results

| hypothesis | result | verdict |
|---|---|---|
| H1 band power vs exponent | band power changed ≥ 30 % in 100 % of cases; peak power within 0.05 log10 in 60.5 % (paired analysis: method bias 0.001) | rejected as registered |
| H2 detection, synthetic | sensitivity 0.847 [0.803, 0.882], 1.68 false/h | rejected |
| H3 volume conduction | wPLI p95 0.193 at 2 min, 0.095 at 10 min; dwPLI 0.021 and 0.006 | rejected at 2 min, accepted at 10 min; dwPLI accepted at both |
| H4 claim checker | 3334/3334 live mutants (fourteen operators), 60/60 faithful | accepted (rejected on the first run) |
| H5 CHB-MIT chb01, detector v1 | 2/7 at 0.52 false/h | rejected |
| H6 CHB-MIT chb03 held out, frozen detector | 4/7 at 3.30 false/h | rejected |
| H7a cloud language model as explainer | gemini-3.8-flash: 30/30 accepted after at most one repair (24 first time) | accepted |
| H7b small local model | qwen2.5:3b: 0/30 accepted; every faulty reply replaced by the template | exploratory |
| H7c blinded audit of accepted text | 3/20 misleading (Wilson [0.05, 0.36]): correct numbers attached to the wrong concept | rejected |

Requirements V-01 to V-04 and P-01 pass (exponent median error 0.014,
alpha frequency 0.067 Hz, specparam agreement 200/200, bad channels 100 %
recall and precision, 12.7 s and 1547 MB for one hour of 32 channels).

## 7. What validation changed

Eight findings, each with its evidence, are in [FINDINGS.md](FINDINGS.md).
The most important: the detector rebuilt the very confound H1 tests (a
raw-spectrum rhythm gate fooled by the 1/f background), and an easy
synthetic benchmark hid three further failure modes (harmonics, normal
alpha/spindle bursts, blink trains) until realistic negatives and
event-free recordings were added. The checker's first-run escape was a
rounding tie; its remaining limit is semantic (a numerically correct
citation of the wrong key).

## 8. Issues and mitigations

Twenty-one dated issues in [BUILD_JOURNAL.md](BUILD_JOURNAL.md), among them:
wPLI bias (ISSUE-001); muscle as the only false-alarm source before
band-limiting (002); negative exponents from an event inside the spectrum
window, found by looking at a figure (004); a circular definition of
"equivalent mutant" caught before it produced a result (006); the rhythm
gate's aperiodic trap (008); an infeasible tuning constraint, revised to
H2's own limit and recorded (010); blink trains merged into "rhythms" (011);
a sign flip written with a typographic minus, reported by an outside reader
and fixed with a new mutation operator (012); and a deliberate bug hunt
(013-021): checker bypasses, damaged files, montage detection, an .npz
decompression bomb, and chewing as a source of false detections.

## 9. Limitations and threats to validity

* **The detector is weak.** Sensitivity on held-out real data was 57 % with
  a wide interval (7 seizures), at 3.3 false detections per hour. It misses
  slow (< 2 Hz) and fast (> 7.5 Hz) ictal rhythms by design of its gate.
  Its output is presented as candidates for review, never as findings.
* **Small real-data base.** Two paediatric subjects, 20 hours, 14 seizures;
  one subject was used for development. Results do not generalise to adults,
  other montages or other recording systems without new tests.
* **Synthetic realism.** The generator has no sleep stages, no evolving
  frequency content beyond a glide, no interictal spikes, and simple
  artifacts. Tuning on it repeatedly proved optimistic.
* **H1 power.** The registered peak-power bound was tighter than the noise
  of the 3-minute design; a longer design would test the method, not the
  noise.
* **Chewing and other artifacts.** On synthetic event-free recordings,
  chewing raised false detections from 2.4 to 6.0 per hour (exploratory,
  ISSUE-021).
* **Non-EEG channels** (ECG, VNS) are excluded from the montage decision and
  the average reference but still enter spectra, coupling and the detector's
  channel vote.
* **Amplitude plausibility.** There is no absolute amplitude or clipping
  check: a file with broken scaling is analysed at implausible amplitudes.
* **Memory with many channels.** Coupling memory grows with the square of
  the channel count (about 0.8 GB at 64 channels for 10 minutes, 2.5 GB at
  128).
* **Checker scope.** Digits only; no semantic check of which key is cited.
* **No adult, clinical or prospective evaluation.** Research use only; not a
  medical device.
* **Single build day.** Tuning choices were made by one person on one day;
  the build journal is the audit trail, not an independent review.

## 10. Future work

1. Spatial cue to separate frontal symmetric blinks from slow ictal delta,
   then lower the gate floor; test on a third held-out subject.
2. A patient-specific or supervised detector with subject-grouped
   cross-validation over more CHB-MIT subjects, compared against this
   unsupervised baseline.
3. Run the LLM explainer (`neurosignal report --explainer llm`, needs an
   API key) on a fixed set of recordings and report its first-pass
   acceptance and repair rates; it has not been run against a live model in
   this version.
4. Longer paired design for H1; multitaper spectra as an alternative
   estimator.
5. A real-time causal plugin with its own latency tests (out of scope here).

## 11. How to reproduce

```bash
make setup && make check        # environment, lint, types, 100+ tests
make data                       # CHB-MIT chb01 + chb03, checksummed
make validate                   # every result file + VALIDATION_REPORT.md
make mutation                   # mutation testing of the test suite
```

All commands: [WORKFLOWS.md](WORKFLOWS.md). Environment pinned by `uv.lock`;
determinism checked in CI.

## 12. References

Benjamini Y, Hochberg Y (1995) *J R Stat Soc B*. · de Cheveigné A, Nelken I
(2019) *Neuron* 102:280. · Donoghue T et al. (2020) *Nat Neurosci* 23:1655.
· Esteller R et al. (2001) Line length: an efficient feature for seizure
onset detection. *Proc IEEE EMBS*. · Gerster M et al. (2022)
*Neuroinformatics* 20:991. · Goldberger AL et al. (2000) *Circulation*
101:e215. · Nolte G et al. (2004) *Clin Neurophysiol* 115:2292. · Robbins KA
et al. (2020) *IEEE TNSRE* 28:1081. · Shoeb AH (2009) PhD thesis, MIT. ·
Trübutschek D et al. (2024) *J Cogn Neurosci* 36(2). · Vinck M et al. (2011)
*NeuroImage* 55:1548. · Widmann A et al. (2015) *J Neurosci Methods* 250:34.
· Ziyabari S et al. (2017) arXiv:1712.10107.
