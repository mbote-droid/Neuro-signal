# Problem statement

Phase 1 of the [engineering playbook](BUILD_JOURNAL.md#playbook). Written
before any code; the hypotheses below were fixed on 2026-10-12, before the
first line of the pipeline existed, and are tested, not tuned, in
[VALIDATION_REPORT.md](VALIDATION_REPORT.md).

## 1. Problem

Researchers and clinicians who receive a scalp EEG recording want a short,
trustworthy summary: is the recording usable, which channels are bad, what
does the spectrum look like, is there rhythmic seizure-like activity, and
which channels are coupled. Today that summary comes from one of two places.
Either a person assembles it by hand in MNE-Python, EEGLAB or FieldTrip,
making a dozen undocumented choices (filter type, direction, reference,
spectral estimator, band limits), or a general-purpose LLM is given the file
or a plot and asked to describe it. The first route is slow and, as
multi-analyst studies show, gives different answers for the same data. The
second gives fluent text whose numbers nobody has checked.

Three specific, well-documented errors make the summary wrong even when the
code runs:

1. **Band power read as oscillation.** A change in canonical band power
   (for example 8-12 Hz "alpha") is reported as a change in an oscillation
   when the aperiodic 1/f exponent moved instead.
2. **Volume conduction read as connectivity.** Phase-locking value and
   coherence are inflated by instantaneous mixing of independent sources
   into many sensors, so "connectivity" appears where none exists.
3. **Unverified explanation.** A narrative report states numbers, channel
   names or diagnoses that the analysis never computed.

Cost: irreproducible results, wasted analysis time, and, when a report
reaches a clinician, false reassurance or false alarm.

## 2. Evidence the problem is real

Sources were compiled on 2026-10-12. Four were checked by web search on that
date (queries recorded); the rest are standard references in the field.
Before publication, every DOI should be re-verified by the author.

| # | source | what it shows | how found |
|---|---|---|---|
| 1 | Trübutschek D, et al. (2024). EEGManyPipelines: a large-scale, grassroots multi-analyst study of EEG analysis practices in the wild. *J Cogn Neurosci* 36(2). doi:10.1162/jocn_a_02087 | 168 teams analysed one EEG dataset with the same hypotheses; analysis choices vary widely | web search 2026-10-12: "EEGManyPipes multi-analyst study EEG analysis Trübutschek 2024" |
| 2 | Robbins KA, Touryan J, Mullen T, Kothe C, Bigdely-Shamlo N (2020). How sensitive are EEG results to preprocessing methods: a benchmarking study. *IEEE TNSRE* 28(5):1081-1090. doi:10.1109/TNSRE.2020.2980223 | 1,100 recordings: preprocessing choice changes amplitudes, spectra and ERPs | web search 2026-10-12: title query |
| 3 | Donoghue T, et al. (2020). Parameterizing neural power spectra into periodic and aperiodic components. *Nat Neurosci* 23:1655-1665 | band-power changes are frequently aperiodic, not oscillatory | standard reference |
| 4 | Gerster M, et al. (2022). Separating neural oscillations from aperiodic 1/f activity: challenges and recommendations. *Neuroinformatics* 20(4):991-1012. doi:10.1007/s12021-022-09581-8 | separation methods (FOOOF, IRASA) have measurable parameter errors; simulated ground truth needed | web search 2026-10-12: title query |
| 5 | Nolte G, et al. (2004). Identifying true brain interaction from EEG data using the imaginary part of coherency. *Clin Neurophysiol* 115:2292-2307 | volume conduction creates spurious zero-lag coupling | standard reference |
| 6 | Vinck M, et al. (2011). An improved index of phase-synchronization ... (wPLI). *NeuroImage* 55:1548-1565 | wPLI is insensitive to zero-lag mixing | standard reference |
| 7 | Ziyabari S, Shah V, Golmohammadi M, Obeid I, Picone J (2017). Objective evaluation metrics for automatic classification of EEG events. arXiv:1712.10107 | sample-level metrics mislead; event-level scoring and false alarms per unit time matter for clinical acceptance | web search 2026-10-12: author + "any-overlap" query |
| 8 | Kapoor S, Narayanan A (2023). Leakage and the reproducibility crisis in machine-learning-based science. *Patterns* 4(9) | evaluation leakage inflates reported accuracy across fields, including EEG | standard reference |
| 9 | de Cheveigné A, Nelken I (2019). Filters: when, why, and how (not) to use them. *Neuron* 102:280-293; Widmann A, et al. (2015) *J Neurosci Methods* 250:34-46 | filter choices (type, direction, cutoff) distort timing and waveform | standard reference |
| 10 | Ji Z, et al. (2023). Survey of hallucination in natural language generation. *ACM Comput Surv* 55(12) | LLM text states unsupported facts; faithfulness must be checked externally | standard reference |

## 3. Existing tools

| tool | what it does | where it falls short for this problem |
|---|---|---|
| MNE-Python | complete M/EEG toolbox: I/O, filtering, ICA, spectra, connectivity (mne-connectivity) | a library, not a report; every choice is the user's; no ground-truth validation of the user's chain |
| EEGLAB / FieldTrip / Brainstorm | MATLAB toolboxes with GUIs and scripting | same; MATLAB licence; GUI choices are hard to record |
| NeuroKit2 | physiological signal processing, strong for ECG/EDA | EEG coverage is thin; no aperiodic or connectivity validation |
| specparam (FOOOF) | aperiodic + peak parameterisation of spectra | one method, not a pipeline; reports nothing about QC, events or coupling |
| SpikeInterface, Kilosort, Suite2p, CaImAn | spike sorting / calcium imaging | other modalities, out of scope |
| General LLM with file upload | fluent summary of a recording or plot | numbers are not computed by validated code, and no claim is checked against the data |

The gap is not a missing algorithm. It is that no tool **ships the validation
with the report**: a deterministic pipeline whose every method has been shown
to recover a known answer, whose every number carries provenance, and whose
narrative text is mechanically checked against those numbers. The measurable
improvement over a general LLM is hypothesis H4; over a hand-built band-power
or PLV analysis, H1 and H3.

## 4. Hypotheses (fixed before building)

Thresholds are pre-registered here; a hypothesis that fails is reported as
rejected, not re-tuned.

* **H1 (aperiodic confound).** On synthetic EEG in which only the aperiodic
  exponent rises by 0.5 and the alpha oscillation is unchanged, canonical
  8-12 Hz band power changes by at least 30 % in at least 95 % of cases,
  while the parameterised alpha peak power changes by at most 0.05 log10
  units in at least 90 % of cases.
* **H2 (event detection, synthetic).** On synthetic recordings with injected
  3 Hz spike-wave discharges at 0 dB SNR or above, the detector reaches an
  event-level sensitivity of at least 0.90, with the Wilson 95 % lower bound
  at least 0.80, and at most 2 false detections per hour.
* **H3 (volume conduction).** When independent sources are mixed into
  sensors with no true coupling, PLV in the alpha band exceeds 0.3 in at
  least 50 % of sensor pairs, while the 95th percentile of wPLI is at most
  0.15. With a truly lagged coupled pair, wPLI exceeds 0.5.
* **H4 (explanation faithfulness).** The claim checker rejects every mutated
  explanation (at least 300 mutants from at least 6 operators; the 95 %
  upper bound on the miss rate, by the rule of three, is then at most 1 %)
  and accepts every faithful explanation produced by the deterministic
  explainer.
* **H5 (transfer to real data, exploratory).** With thresholds chosen on
  synthetic data only, the detector finds at least 5 of the 7 expert-marked
  seizures in the CHB-MIT chb01 subset at no more than 2 false detections
  per hour. This tests whether synthetic validation transfers; failure is an
  informative result, not a defect to hide.

## 5. Stakeholders

| stakeholder | interest |
|---|---|
| EEG researcher | a fast, reproducible first look at a recording, with parameters stated |
| clinician | must never receive a diagnosis from a research tool; needs clear research-use-only labelling |
| patient / data subject | identifiable header data must not leak into reports, logs or figures |
| reviewer | every number traceable to code, data and seed |
| future maintainer | methods swappable without touching the core; tests that catch regressions |
| adversary | a malformed or oversized file aimed at the parser; an LLM that invents numbers |

## 6. System framing

```
brain -> electrodes -> amplifier/ADC -> EDF file -> [reader] -> QC -> preprocessing
      -> features (spectrum, aperiodic, coupling, events) -> metrics.json
      -> explanation (deterministic or LLM) -> claim checker -> report -> reader of report
```

The **sensor whose errors propagate** is the metrics layer: an error there
(a wrong exponent, a spurious coupling) is passed verbatim into the
narrative. The claim checker is the second sensor; it is itself validated by
mutation testing (H4).

## 7. Scope

* **In scope:** offline scalp EEG (EDF/EDF+, BDF, BrainVision; native `.npz`
  for synthetic data); QC; zero-phase FIR filtering; line-noise notch;
  common-average reference for referential montages; Welch spectra;
  aperiodic/periodic parameterisation; alpha-band wPLI and PLV; rhythmic
  seizure-like event detection; JSON metrics with provenance; Markdown and
  HTML report; deterministic explainer; optional LLM explainer; claim checker.
* **Out of scope:** real-time streaming, ICA, source localisation, spike
  sorting, decoding/BCI, other modalities.
* **Ruled out:** any diagnostic statement. The tool is research use only and
  not a medical device.

## 8. Success metrics

| metric | measured how | threshold |
|---|---|---|
| aperiodic exponent error | synthetic spectra, known exponent | median absolute error <= 0.1 |
| alpha peak frequency error | synthetic spectra, known peak | median absolute error <= 0.5 Hz |
| bad-channel recall / precision | injected flat and noisy channels | both >= 0.95 |
| H1-H5 | as stated above | as stated above |
| determinism | same file and seed, two processes | byte-identical metrics.json |
| resources | 1-hour, 32-channel, 256 Hz synthetic recording | peak RSS <= 2 GB, runtime <= 5 min on one core |

## 9. Addendum (2026-10-12): pre-registered held-out test H6

Written after H5 was evaluated on CHB-MIT chb01 and the rhythm gate was
revised (BUILD_JOURNAL ISSUE-008), and **before any chb03 file was
downloaded or inspected**. chb01 has become a development set: every
result on it after the revision is post hoc.

* **H6 (held-out transfer).** With the revised detector (background-
  normalised rhythm gate) and thresholds re-chosen on synthetic tuning
  seeds only, applied once and unchanged to CHB-MIT subject chb03, the
  detector finds at least 60 % of the expert-marked seizures with at most
  2 false detections per hour.
* **Files:** every chb03 file that the subject summary lists with at least
  one seizure, plus the first three files listed without seizures (false-
  alarm exposure). Chosen by this rule before downloading.
* **No changes after the run.** Whatever the result, it is reported as is;
  any later change to the detector needs another untouched subject.

**Frozen detector for H6.** The detector tested on chb03 is the one at the
commit that adds this paragraph: 1-20 Hz line length, robust z > 2.5,
one-channel vote, events of at least 10 s, 1 s merge gap, and a rhythm gate
on the fundamental of the background-normalised spectrum in 2-7.5 Hz
(BUILD_JOURNAL ISSUE-008 to ISSUE-011). chb03 data had not been downloaded
when this was committed.

## 10. Addendum (2026-10-18): pre-registered evaluation of the LLM explainer, H7

Written after release v0.1.1 and **before any live model was called**. H4
showed that the claim checker rejects mutated explanations; it said nothing
about how real models behave under the citation contract. H7 tests that.

* **Recordings.** 30 synthetic recordings from the explanation generator
  used for H4 (`validation/common.py: explanation_metrics`), seeds
  100-129, disjoint from H4's seeds 0-59.
* **Models.** Two, chosen by the author before the run and not changed
  after seeing any output: one cloud model on Google's free Gemini API tier
  and one small open model (3-4 billion parameters) run locally with
  Ollama. The exact model identifiers and versions reported by each API are
  written into the result files.
* **Procedure.** The system prompt and citation contract of
  `explain/llm.py` at this commit, unchanged; temperature 0; at most one
  repair round with the checker's findings (as in the shipped explainer).
  One run per model. A run interrupted by rate limits or network errors is
  resumed, never restarted; only calls that failed for infrastructure
  reasons are retried, never calls whose text the checker rejected.
* **H7a (cloud model).** At least 24 of 30 explanations (80 %) are
  accepted by the checker after at most one repair.
* **H7b (local model, exploratory).** Acceptance rates are reported with
  Wilson intervals; no threshold. A small local model is expected to break
  the contract more often; how often is the result.
* **H7c (blinded audit, both models).** A random sample of up to 20
  accepted explanations per model (fixed seed), pooled and shuffled with
  the model hidden, is read by the author against the metrics they cite.
  An explanation fails the audit if it contains at least one statement that
  is false or misleading given the metrics (a citation of the wrong metric
  for the sentence, a wrong interpretation, or an invented qualitative
  claim): the errors the checker cannot see (FINDINGS F-4). For the cloud
  model, at most 2 of 20 audited explanations fail. The local model's rate
  is reported. The auditor built the tool and is not independent; this is
  stated with the result.
* **Reported in all cases.** First-pass acceptance, acceptance after
  repair, the checker's finding codes, and latency, per model. Whatever
  the result, it is reported as is; prompt changes after the run need a new
  set of recordings.

**Models chosen for H7 (2026-10-21, before any H7 call).** Cloud:
`gemini-3.8-flash` on the Gemini API free tier (5 requests per minute,
20 per day, so the run is resumed over several days as §10 allows). Local:
`qwen2.5:3b` served by Ollama 0.40.1, model ID `357c53fb659c` (4-bit,
1.9 GB). The local model is within the registered 3-4 billion parameters.

**Amendment (2026-10-22, before any H7 result existed).** After H7 was
registered, an outside report (issue #21, BUILD_JOURNAL ISSUE-012) showed
that the checker missed sign flips written with a typographic minus. The
shipped checker was corrected. H7's primary verdicts (H7a-c) still use the
checker as registered, kept as a hash-pinned copy
(`validation/h7_registered_checker.py`); the corrected checker is applied
to the same saved replies as a secondary analysis, reported alongside
(`llm_eval.py recheck`). No model call is repeated for it.

## 11. Addendum (2026-10-31): development criteria for a spatial blink cue (v0.2)

Written before any code for the cue exists and before any measurement of
it. This is a **development step**, not a confirmatory test: its purpose is
to decide whether the cue enters the detector that will later be frozen for
a confirmatory test on new subjects (ROADMAP, step 4). **chb03 is not used
in any form**: it was the one-shot held-out test of H6 and is spent. chb01
is a development set; anything measured on it is optimistic by
construction.

**Motivation (FINDINGS F-7).** All three seizures missed on chb03 passed the
line-length stage but had fundamentals of 1.0-1.5 Hz, below the rhythm
gate's 2 Hz floor. The floor exists to reject blink trains (F-6, ISSUE-011),
which band-limited to 1-20 Hz look like a 1.5-2 Hz rhythm. Blinks have a
field that slow ictal rhythms usually lack: frontopolar, bilateral and
symmetric. If that field can be measured, the floor can come down below
2 Hz for events that do not have it.

**The cue (fixed now).** For a candidate event, using the detector's
band-limited signal (1-20 Hz) and only analysed channels:

* the *anterior electrode* of a channel is its name in a referential
  montage, and the first electrode `A` of a derivation `A-B`;
* *frontopolar* channels are those whose anterior electrode is Fp1, Fp2,
  Fpz, AF3, AF4, AF7, AF8 or AFz (case-insensitive); *left* are Fp1, AF3,
  AF7 and *right* Fp2, AF4, AF8; all other analysed channels are *other*;
* per channel, *excess* = RMS of the event segment / RMS of the whole
  recording;
* *frontality* = median excess over frontopolar channels / median excess
  over other channels;
* *symmetry* = min(mean left excess, mean right excess) / max of the two;
* an event is *blink-like* when frontality >= F* and symmetry >= S*.

**The gate (fixed now).** An event is kept, as today, when its fundamental
lies in 2-7.5 Hz. In addition, an event whose fundamental lies in
[f_low, 2 Hz) is kept when the cue is available and the event is not
blink-like. The cue is unavailable when no left, no right or no other
channel is analysed (frontopolar electrodes missing or marked bad); such
events are rejected below 2 Hz, exactly as today. Events at 2 Hz and above
are never affected by the cue.

**Tuning (fixed now), on synthetic tuning seeds 0-59 only.** Three
populations, each rendered in the referential montage (as generated) and in
the 18-derivation longitudinal bipolar montage of CHB-MIT (derived from
the same signals): (a) the standard benchmark recordings; (b) the same with
the discharges slowed to a fundamental gliding within 1.0-1.8 Hz. Grid:
f_low in {1.0, 1.5} Hz; F* in {1.5, 2, 3, 4}; S* in {0.5, 0.7}. The other
detector thresholds stay as frozen for H6. **Rule:** among settings with at
most 2 false detections per hour over all tuning recordings in both
montages, choose the highest sensitivity on the slowed discharges; break
ties towards the setting that admits less (higher f_low, then lower F*,
then lower S*). The full grid is saved whatever the outcome.

**Stop rule.** If no setting meets the false-detection constraint, or the
selected setting finds fewer than half of the slowed discharges on the
tuning seeds, the cue is not adopted, the 2 Hz floor stays, and the result
is reported as negative.

**Evaluation (fixed now), once, on evaluation seeds 1000-1199** (never used
for tuning), with the selected setting and with the cue off as a baseline:

* **D1 (no regression).** Standard benchmark, referential: sensitivity at
  least 0.847 (the H2 result) and at most 2 false detections per hour.
* **D2 (slow discharges).** Slowed benchmark, both montages pooled:
  sensitivity at least 0.70 with a Wilson 95 % lower bound of at least
  0.60.
* **D3 (bipolar montage).** Standard benchmark, bipolar: at most 2 false
  detections per hour.
* **D4 (artifacts).** On the event-free adversarial recordings (seeds
  2000-2019: baseline, eye flutter, chewing, electrode pops, sweat), false
  detections per hour with the cue are at most the cue-off rate plus
  0.5 per hour for each artifact.
* **D5 (the cost of the veto, reported).** Discharges centred on Fp1, Fp2,
  F7 or F8, at normal and slowed frequency: sensitivity with and without
  the cue. Normal-frequency sensitivity must be identical (the cue does not
  act at 2 Hz and above); slowed frontal sensitivity is reported as the
  cue's known cost, with no threshold. A bilateral, symmetric frontopolar
  slow seizure is blink-like by this definition and would be rejected.
* **D6 (chb01, development, reported).** Seizures found and false
  detections per hour, with and without the cue. Not a test.

**Decision.** The cue is switched on in the shipped detector only if D1-D4
all pass. Otherwise it stays off and the result is reported as negative.
Either way, any later change to the detector needs the confirmatory test
on untouched subjects (ROADMAP step 4) before a detection claim is made.

**Amendment to §11 (2026-10-31, before any tuning or evaluation run).**
*Excess* is redefined as the RMS of the event segment over the channel's
**median RMS across non-overlapping 2 s windows**, instead of over the RMS of
the whole recording. A unit test with a constructed signal showed the
registered definition was wrong: the whole-recording RMS contains the event
it is compared with, which caps a strong event's excess near
sqrt(recording length / event length). A textbook blink field (Fp1 = Fp2 =
1, frontal row 0.4) scored a frontality of 2.2 in a 120 s recording instead
of about 4. Nothing else changes: the gate, the grid, the tuning rule, the
stop rule and D1-D6 stand as registered. No tuning, evaluation or real
recording had been run with either definition.

## 12. Addendum (2026-10-31): a baseline that excludes the events it measures (v0.2, step 2b)

Written before the change exists in the detector and before the detector has
been run with it. A development step: it decides whether the change enters
the detector that will later be frozen for the confirmatory test (ROADMAP
step 4). chb03 is not used; chb01 is development.

**What the exploratory diagnosis found** (`results/validation/montage_diagnosis.json`,
`montage_power.json`; synthetic tuning seeds and fresh seeds 5000-5199, never
used for tuning or evaluation):

* With one source of negatives at a time and no discharges, the frozen
  detector's false-alarm rate does not depend on the montage (full set: 4.50
  vs 4.30 per hour). Normal alpha and spindle bursts cause most of it (4.0/h).
* On 200 fresh benchmark recordings the bipolar rendering raised false alarms
  from 1.80 to 2.67 per hour (more on 30 recordings, fewer on 8; sign test
  p = 0.0005), but the same recordings with their discharges removed gave
  4.17 and 4.65 per hour (p = 0.15).
* The mechanism: each channel's robust z-score is scaled by the spread of log
  line length over the whole recording, which contains the discharges. They
  widen it by a median factor of 1.31 in the referential montage, where the
  common average carries a discharge into every channel, and 1.09 in the
  bipolar one. Every other burst then looks less extreme, more so in the
  referential montage. The benchmark's false-alarm rate is therefore lowered
  by its own discharges: in the published H2 rows, event-free recordings
  ran at 2.85 per hour against 1.39 with discharges.
* Measuring the baseline outside the windows where the detector is active
  removed the effect: median factors 1.002 (referential) and 1.006
  (bipolar).

**The change (fixed now).** The z-score is computed in two passes. Pass 1 is
today's: per channel, median and MAD of log line length over all windows. A
window is *active* when at least `channel_fraction` of the channels exceed
`z_threshold` in pass 1; each active window is widened by one step on each
side. Pass 2 recomputes each channel's median and MAD over the windows that
are not active, and the final z-scores use them. If fewer than half of the
windows are left, pass 1 is kept (a recording that is mostly active has no
quiet baseline to measure). No new threshold is introduced.

**Tuning (fixed now), synthetic tuning seeds 0-59 only.** Because the
discharges no longer lower the false-alarm rate, the detector's thresholds
are re-chosen with the rule and grids already used for H2
(`validation/tune_detector.py`): among settings with at most 2 false
detections per hour, the highest sensitivity, ties broken towards the more
conservative setting. The false-alarm constraint and the sensitivity are
pooled over the standard benchmark rendered in both the referential and the
CHB-MIT bipolar montage. The blink cue (§11) stays off. The full grid is
saved whatever the outcome.

**Stop rule.** If no setting meets the constraint, the change is not adopted
and the detector frozen for H6 stays; the result is reported as the honest
false-alarm rate of a detector that the benchmark had flattered.

**Evaluation (fixed now), once, on evaluation seeds 1000-1199**, with the
selected setting, both montages:

* **E1 (false alarms).** At most 2 false detections per hour in each montage,
  over all recordings and over the event-free recordings separately.
* **E2 (montage).** Bipolar false alarms at most 0.5 per hour above
  referential.
* **E3 (sensitivity).** At least 0.80 in each montage.
* **E4 (mechanism).** On the recordings with discharges, the median ratio of
  each channel's spread with and without its discharges lies within
  0.95-1.05 in both montages.
* **E5 (chb01, development, reported).** Seizures found and false detections
  per hour, frozen detector against the new one. Not a test.
* **Reported in all cases:** the frozen detector's rates on the same
  recordings, overall and event-free, in both montages.

**Decision.** The change and the re-tuned thresholds enter the shipped
detector only if E1-E4 all pass. Results measured with the frozen detector
(H2, H5, H6) are not re-labelled: they stay the results of that detector.
