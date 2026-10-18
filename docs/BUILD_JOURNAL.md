# Build journal

Dated log of decisions, issues and mitigations, written as the build went
(playbook §12). Numbers link to result files where they exist. All entries
are from the first build on 2026-10-12.

<a id="playbook"></a>
**Process.** The project followed the author's neuroscience engineering
playbook (problem, requirements, architecture, design, proof of concept,
build, validation, report), carried over from BioEng-TermBench. The commit
history shows the order: problem statement and hypotheses first, then
requirements, then architecture, then code; the held-out test H6 was
committed before its data were downloaded.

## Decisions (become ADRs)

* **Modality and workflow.** Scalp EEG, one workflow ("drop a file, get a
  validated report"), per the portfolio roadmap's Phase 3. Rejected for now:
  spike sorting (option B) and real-time BCI (option C); the aperiodic audit
  (option D) and the EEG/seizure option (A) were combined because both fit
  one report and share the synthetic generator.
* **Real data access.** PhysioNet's site was not reachable from the build
  environment; the same files (and PhysioNet's SHA-256 list) are served by
  PhysioNet's open-data mirror on AWS, which `scripts/fetch_chbmit.py` uses.
* **PoC go decision.** The vertical slice (synthetic file -> filter ->
  detector -> report) ran end to end in 3.4 s for 5 minutes of 19-channel
  data, and the initial, untuned detector (z = 4, 30 % channel vote) found
  the chb01_03 seizure (2996-3036 s) with no false detection in that file.
  Go. That single PoC look at chb01_03 happened before tuning and is
  disclosed here because chb01 was later the H5 test set.

## Issues

### ISSUE-001 wPLI is far from zero when nothing is coupled   (2026-10-12)
Phase: PoC
Symptom: on six independent mixed sources (no coupling at all), the 95th
percentile of wPLI over sensor pairs was 0.18-0.22 with 120 s of data,
above the pre-registered 0.15.
Root cause: wPLI's estimator $|\sum \operatorname{Im} S| / \sum |\operatorname{Im} S|$
is non-negative and biased upwards with few epochs (60 here). Established by
running 120, 300 and 600 s: the 95th percentile fell to 0.11 and 0.08-0.12
as epochs increased, while the debiased squared estimator stayed at
0.00-0.04 at every length.
Mitigation: report the debiased squared wPLI (Vinck et al. 2011) as the
primary measure; keep wPLI and PLV in `metrics.json` for comparison.
Verification: `tests/test_connectivity.py`; `connectivity.json`.
Impact: H3 as registered (plain wPLI) is rejected at 120 s and accepted at
600 s; reported both ways in the validation report and FINDINGS.
Lesson: pre-register the estimator, not only the measure.

### ISSUE-002 Muscle bursts were the only source of false detections   (2026-10-12)
Phase: implementation (detector)
Symptom: first tuning grid could not reach 1 false detection per hour on
the tuning seeds at any setting (best: 7.9/h at sensitivity 0.55).
Root cause: ablation on ten seeds: removing muscle bursts took false
detections from 34 to 0; removing blinks changed nothing. Line length rises
with any high-frequency energy.
Mitigation: compute line length on the 1-20 Hz band only (ictal rhythms
are below 20 Hz; EMG is mostly above). False detections fell from 34 to 10
on the same seeds. Alternative considered: an EMG detector (more code,
another threshold).
Verification: `detector_tuning.json` (grid before/after recorded in this entry).

### ISSUE-003 Focal discharges fail a channel vote; CAR spreads them   (2026-10-12)
Phase: implementation (detector)
Symptom: a 10 dB discharge on four channels was missed; two of its four
channels had been marked bad, leaving 2/17 channels, below the 20 % vote.
On another seed a discharge raised z to about 4 on every channel.
Root cause: (1) a fractional vote penalises focal events; (2) the common
average reference subtracts 1/|G| of a large focal discharge from every
channel.
Mitigation: the vote fraction became a tuned parameter (the rule selected
one channel); CAR's spreading is documented in EQUATIONS §3 rather than
removed (CAR is still right for the spectral and coupling measures).
Lesson: reference choice is a detection design decision, not only a
preprocessing one.

### ISSUE-004 Negative aperiodic exponents on discharge channels   (2026-10-12)
Phase: implementation (found in the first report figure)
Symptom: T7, P7 and P8 showed exponents of about -1 in a synthetic report.
Root cause: a 3 Hz spike-wave discharge with harmonics dominates 2-10 Hz on
the involved channels; the aperiodic fit in 2-40 Hz bends to fit it.
Mitigation: detect events first, then estimate spectra and coupling only
outside them (`welch(..., exclude=...)`); flag fits with R² < 0.8 or an
exponent outside [0, 4] as unreliable and leave them out of averages.
Verification: exponents on the same file became 1.26-1.73;
`tests/test_spectral.py::test_excluded_windows_are_dropped`.
Lesson: look at the figures; the unit tests all passed.

### ISSUE-005 Blinks and muscle passed the detector as "rhythmic" events   (2026-10-12)
Phase: implementation (detector)
Symptom: after ISSUE-002, sensitivity was 0.60 at the 1 false/h constraint.
Root cause: characterising 167 detections on 40 tuning seeds: every true
discharge had its dominant frequency at 2.5-4 Hz; false detections peaked at
the band edges, 1 Hz (blinks, drift) or about 20 Hz (muscle leaking in).
Mitigation: rhythmicity gate, dominant frequency within 2-13 Hz (delta to
alpha; from physiology, not tuned). Tuning sensitivity rose to 0.93 at
0.6 false/h.
Verification: `test_negative_control_rhythm_gate_removes_muscle_false_alarms`
(27 false detections without the gate, 2 with it).

### ISSUE-006 A circular definition of "equivalent mutant"   (2026-10-12)
Phase: validation design
Symptom: the first draft of `validation/mutants.py` called a mutant
equivalent if the checker accepted it.
Root cause: that definition turns every escape into an "equivalent mutant",
so H4 could never fail. Caught on review before any result was produced.
Mitigation: each operator decides equivalence from the metric values with
its own rounding rule (integer arithmetic, separate from the checker's
code).
Lesson: a validator's oracle must not be the validator.

### ISSUE-007 One mutant escaped the claim checker (rounding tie)   (2026-10-12)
Phase: validation (H4, first full run)
Symptom: 2152/2153 live mutants caught. The escape wrote "1" while citing a
metric equal to 0.5.
Root cause: the checker accepted |w - v| <= half a unit (0.5 <= 0.5), the
independent oracle used round-half-to-even ("0"). An exact tie is
ambiguous between rounding conventions. The mutant also showed a deeper
limit: the checker verifies that numbers trace to metrics, not that a
cited key fits the sentence ("1 [[processing.1.highpass_hz]] channels").
Mitigation: strict rule |w - v| < half a unit in both checker and oracle;
the template adds a decimal whenever it would write a tie. Semantic key
relevance is documented as a limitation.
Verification: `test_precision_rule` (tie case); re-run 2153/2153 caught,
60/60 faithful accepted.
Impact: H4 rejected on the first run, accepted after the fix; both reported.

### ISSUE-008 The rhythm gate fell into the aperiodic trap on real EEG   (2026-10-12)
Phase: validation (H5)
Symptom: H5 rejected: 2 of 7 chb01 seizures detected; both detections
reported a dominant rhythm of exactly 2.0 Hz, the gate's lower edge.
Root cause: diagnosis of the candidates before the gate: the line-length
stage found all 7 seizures, but the raw event spectrum of real EEG peaks at
1-2 Hz because of the 1/f background, so the gate rejected them. Synthetic
discharges were strong enough to dominate the raw spectrum, which hid the
problem. This is the H1 confound inside the detector.
Mitigation: the gate reads the peak of the event spectrum divided by the
background spectrum of the same channels. Thresholds re-chosen on synthetic
tuning seeds by the same rule. chb01 is a development set from here on, and
a held-out test (H6, subject chb03) was pre-registered and committed before
download.
Lesson: a confound you have just demonstrated (H1) is easy to rebuild in
your own code.

### ISSUE-009 Normal alpha and spindle bursts became false detections   (2026-10-12)
Phase: development on chb01
Symptom: with the background-normalised gate, 5 of 7 chb01 seizures were
found but with 51 false detections (5.3/h); most had a ratio peak at
8-13 Hz (one 227 s run at 11 Hz in chb01_02).
Root cause: posterior alpha bursts and spindle-like 11-15 Hz trains are
normal rhythms that rise above a recording's own baseline; the synthetic
benchmark contained none, so tuning could not see them.
Mitigation: model the failure in simulation first: add alpha bursts
(3-30 s, 8-13 Hz, posterior) and spindles (0.8-2.5 s, 11-15 Hz, central) to
the generator, add the gate's upper limit (13 vs 8 Hz) to the tuning grid,
and let the synthetic rule choose. Then freeze the detector before chb03.
Verification: see `detector_tuning.json` and the H2/H6 results.

### ISSUE-010 Harmonics, an 8.0 Hz bin edge, and an infeasible constraint   (2026-10-12)
Phase: development (synthetic, after ISSUE-009)
Symptom: with alpha and spindle bursts simulated, no grid setting met the
1 false/h tuning constraint (best 1.3/h at sensitivity 0.48); with the
2-8 Hz gate, sensitivity fell to 0.70.
Root cause, established by listing every candidate on 20 tuning seeds:
(1) dividing by the 1/f background boosts the harmonics of a spike-wave
train, so the largest peak of the ratio was often at 6-9 Hz instead of the
2.5-5 Hz fundamental; (2) alpha bursts drawn at 8.0-8.25 Hz fall into the
8.0 Hz Welch bin and passed an inclusive "<= 8 Hz" gate. A third hypothesis,
that the common average reference spread posterior alpha into frontal
channels, was tested (detection with and without CAR on 20 seeds) and
rejected: no change at 2-13 Hz.
Mitigation: the gate reads the fundamental (lowest peak at least half the
largest) of the background-normalised spectrum; the delta-theta option is
2-7.5 Hz. On 20 tuning seeds the fundamental raised sensitivity from 0.70
to 0.83 at the narrow gate. The tuning constraint was revised from 1 to
2 false detections per hour, H2's own pre-registered limit, because the
original one had no feasible setting; both the infeasible grid
(`detector_tuning_infeasible.json`) and the revision are kept.
Lesson: a realistic negative class (normal rhythms) is worth more than any
amount of tuning on an easy one.

### ISSUE-011 Blink trains posed as 2.5 Hz rhythmic events   (2026-10-12)
Phase: development (synthetic)
Symptom: after ISSUE-010 the selected setting (z = 2.5) produced
detections in 5 of 8 five-minute event-free recordings, and the false rate
on 30 event-free ten-minute recordings was 6.4-6.6/h at z = 2.5, 3 and 4
alike, far above the 1.9/h on the tuning set.
Root cause: a blink band-limited to 1-20 Hz is a biphasic wave with most
energy near 2-3 Hz; at 15 blinks per minute, consecutive blinks were merged
across the fixed 5 s gap into one long event whose fundamental (2.5 Hz)
passed the gate. Detections were independent of z because blink line
length is far above any threshold. The tuning set hid it: every tuning
recording contained two discharges, and long merged blink runs that touched
a discharge counted as hits.
Mitigation: the merge gap (1, 2 or 5 s) joins the tuning grid; one tuning
and evaluation recording in five is now event-free, so false detections on
clean background are part of the objective.
Lesson: include the null case in every tuning set; a detector tuned only on
recordings that contain events learns to call everything an event.
