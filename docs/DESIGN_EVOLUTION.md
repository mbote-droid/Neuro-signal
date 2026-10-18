# Design evolution: from plan to what was built, and why

This is the project's story in the order it happened: what was planned,
what the evidence said, what changed, how we know each change was right, and
what the changes do and do not guarantee. The details live elsewhere (the
[build journal](BUILD_JOURNAL.md) for each issue, [FINDINGS](FINDINGS.md) for
what validation changed, [STATISTICAL_FOUNDATIONS](STATISTICAL_FOUNDATIONS.md)
for the theory); this document connects them.

**How to read the evidence.** Every result is labelled:
* **confirmatory**: a hypothesis or test fixed in writing before the data
  were seen (H1-H6; their commits precede their results);
* **exploratory**: measured after looking, used to decide what to try next.

Times are commit times from the git history (2026-10-12 unless stated).
Some commits bundle several steps; the build journal records the finer order.

---

## Part 1. The plan (21:42-21:44)

Three commits came before any code: the problem statement with hypotheses
H1-H5 (`1d92eb4`), the requirements (`377fa3b`), and the architecture with
twelve decision records (`789d1e8`). The plan for each component:

| component | planned design | why it seemed right |
|---|---|---|
| reader | MNE adapters, µV, refuse unknown or oversized files | mature parsers; the classic unit error made impossible |
| filtering | zero-phase FIR, 0.5-45 Hz, 50 Hz notch | offline analysis, no timing shift |
| reference | common average, skipped for bipolar montages | standard for dense referential EEG |
| spectra | Welch over the whole recording | 0.5 Hz resolution, low variance |
| oscillations | own specparam-style fit, specparam as oracle | separates peaks from the 1/f background (H1) |
| coupling | wPLI, with PLV as contrast | robust to volume conduction (H3) |
| events | line length, robust z > 4, 30 % channel vote, events of at least 8 s, 5 s merge gap | cheap, unsupervised, no labels to leak |
| tuning | thresholds from synthetic data only | no double dipping on real data |
| synthetic truth | 1/f background + alpha + spike-wave discharges + blinks + muscle + bad channels | known answers for every method |
| explanation | template or LLM, citations checked by a rule-based checker | numbers must be traceable (H4) |
| real-data test | CHB-MIT chb01, run once (H5) | public expert labels |

## Part 2. Proof of concept (22:08)

The thinnest vertical slice (synthetic file → filter → detector → report)
ran end to end in 3.4 s for 5 minutes of 19-channel data, and the untuned
detector found the chb01_03 seizure with no false detection in that file.
**Go.** That single look at a chb01 file, before tuning, is disclosed because
chb01 later served as the H5 test set.

## Part 3. Turning points

Each turning point follows the same pattern: trigger (evidence), root cause
(how it was established), alternatives, decision, proof.

### T1. A coupling measure that reports coupling where there is none

* **Trigger (exploratory).** With six independent sources mixed into 19
  sensors, plain wPLI's 95th percentile was 0.18-0.22 at 2 minutes, above
  H3's pre-registered 0.15.
* **Root cause.** Small-sample bias of the estimator, established by running
  2, 5 and 10 minutes: the bias fell as epochs grew, the debiased estimator
  stayed at zero.
* **Decision.** Report debiased wPLI² (Vinck et al. 2011); keep wPLI and PLV
  in `metrics.json` for comparison.
* **Proof.** Theory predicts E[wPLI | no coupling] ≈ 2/√(πN): 0.1457 at
  60 epochs; measured 0.1455. Debiased: 0.0003. The failure was computable
  in advance.
* **Verdict on H3 (confirmatory).** Rejected at 2 minutes, accepted at 10;
  the debiased estimator passes at both.

### T2. False alarms that were all muscle

* **Trigger.** The first tuning grid could not reach 1 false detection per
  hour at any setting (best 7.9/h at sensitivity 0.55).
* **Root cause.** Ablation on ten seeds: removing muscle bursts took false
  detections from 34 to 0; removing blinks changed nothing.
* **Alternatives.** A separate EMG detector (more code, another threshold)
  vs restricting line length to 1-20 Hz, where ictal rhythms live and most
  muscle activity does not.
* **Decision.** Band-limit first. **Proof:** 34 → 10 false detections on the
  same seeds.

### T3. Focal events and the reference

* **Trigger.** A 10 dB discharge on four channels was missed: two of those
  channels had been marked bad, leaving 2 of 17, below the 20 % vote then
  being tried.
* **Decision.** The vote fraction became a tuned parameter (the rule later
  chose one channel). The common average reference was kept for spectra
  and coupling; its side effect of spreading a large focal discharge across
  all channels is documented. Later (T10) the hypothesis that this spreading
  caused false alarms was tested on 20 seeds and rejected.

### T4. A figure caught what the tests did not

* **Trigger.** The first synthetic report showed aperiodic exponents of
  about −1 on three channels. All unit tests passed.
* **Root cause.** The 3 Hz discharge and its harmonics dominated those
  channels' 2-10 Hz spectrum, and the 1/f fit bent to follow them.
* **Decision.** Detect events first, then estimate spectra and coupling only
  outside them; flag fits with R² < 0.8 or an exponent outside [0, 4].
  **Proof:** exponents on the same file became 1.26-1.73.
* **Lesson.** Look at the output, not only the test results.

### T5. A rhythm gate, first version

* **Trigger.** After T2, sensitivity was 0.60 at 1 false/h.
* **Root cause.** Characterising 167 detections: true discharges had dominant
  frequencies of 2.5-4 Hz; false ones peaked at the band edges (1 Hz blinks,
  20 Hz muscle leakage).
* **Decision.** Keep an event only if its dominant frequency lies in
  2-13 Hz, a band set by physiology, not tuning.
  **Proof:** tuning sensitivity 0.60 → 0.93 at 0.6 false/h.

### T6. A validator that could not fail

* **Trigger.** Review of the first mutation-testing code for the claim
  checker: a mutant was called "equivalent" if the checker accepted it.
* **Root cause.** Circular oracle: every escape would have been relabelled
  equivalent, so H4 could never fail.
* **Decision.** Each mutation operator decides equivalence from the metric
  values with its own rounding rule (integer arithmetic), never through the
  checker. Caught before any result was produced.

### T7. First full campaign (22:59): the checker's one escape

* **Confirmatory result, H4, first run.** 2152 of 2153 live mutants caught.
  The escape wrote "1" for a metric equal to 0.5: the checker accepted the
  tie (|1 − 0.5| ≤ 0.5), the independent oracle (round half to even) did not.
* **Decision.** Strict tie rule in both; the template never writes a tie.
  Second run: 2152/2152 caught, 60/60 faithful explanations accepted.
  Reported as rejected on the first run, accepted on the second.
* **Also learned.** The checker cannot tell whether a cited key fits the
  sentence (a channel count citing a filter cutoff passed numerically). A
  stated limit, not a fixed one.

### T8. The detector fell into the trap H1 describes

* **Confirmatory result, H5.** 2 of 7 chb01 seizures at 0.52 false/h:
  rejected. Both detections reported exactly 2.0 Hz, the gate's lower edge.
* **Root cause.** All seven seizures passed the line-length stage, but real
  EEG's raw spectrum peaks at 1-2 Hz because of the 1/f background, so the
  gate rejected them. Strong synthetic discharges had hidden this. It is the
  same confound H1 tests, rebuilt inside our own detector.
* **Decision.** The gate reads the event spectrum *divided by the
  background spectrum of the same channels*.
* **Process decision.** chb01 became a development set; every later chb01
  number is exploratory. A new held-out test, **H6 on subject chb03**, was
  pre-registered and committed (`ed41812`, 22:41) before any chb03 file was
  downloaded.

### T9. Normal brain rhythms the benchmark did not contain

* **Trigger (exploratory, chb01).** With the normalised gate, 5 of 7
  seizures were found, but with 51 false detections (5.3/h), most at
  8-13 Hz: posterior alpha bursts and spindle-like trains.
* **Decision.** Model the failure in simulation before fixing it: alpha
  bursts (3-30 s, 8-13 Hz) and spindles (0.8-2.5 s, 11-15 Hz) were added to
  the generator, and the gate's upper limit (13 or 8 Hz) joined the tuning
  grid, so the synthetic rule chose it rather than chb01.

### T10. Harmonics, a bin edge, and an impossible constraint (23:18)

* **Trigger.** With realistic normal rhythms, no setting met the 1 false/h
  constraint (best 1.3/h at sensitivity 0.48).
* **Root causes, from listing every candidate on 20 seeds.**
  1. Dividing by a 1/f background boosts a spike-wave train's harmonics
     above its fundamental.
  2. Alpha bursts at 8.0-8.25 Hz fall in the 8.0 Hz bin and passed a
     "≤ 8 Hz" gate.
  3. (Tested and rejected: the reference spreading alpha frontally.)
* **Decisions.** The gate reads the fundamental (lowest peak at least half
  the largest); the delta-theta option became 2-7.5 Hz. The tuning
  constraint was relaxed from 1 to 2 false/h, H2's own pre-registered limit,
  with the infeasible grid kept as evidence.
  **Proof:** at the narrow gate, sensitivity 0.70 → 0.83 on 20 seeds.

### T11. Blinks posing as rhythms (23:23)

* **Trigger.** On event-free recordings the detector made 6.4-6.6 false
  detections per hour regardless of the threshold.
* **Root cause.** A blink band-limited to 1-20 Hz is a ~2 Hz wave; at
  15 blinks per minute, the fixed 5 s merge gap joined consecutive blinks into
  long "rhythmic" events. The tuning set hid it: every tuning recording
  contained real events.
* **Decisions.** One recording in five is now event-free; the merge gap is
  tuned (1 s selected).
* **Proof (theory, later).** A Poisson model of supra-threshold blinks
  predicts 13.7 long runs per hour at a 5 s gap and 0.07 at 1 s; measured 21.9
  and 0.3. The gap alone moves blink false events by two orders of magnitude.

### T12. Freeze, then one held-out run (23:28-23:35)

* The detector was frozen and committed (`36b7964`) before chb03 existed on
  disk: z > 2.5, one-channel vote, ≥ 10 s, 1 s gap, fundamental gate 2-7.5 Hz.
* **Confirmatory results.** H2 (synthetic, now with realistic negatives):
  sensitivity 0.847 [0.803, 0.882] at 1.68 false/h, rejected. **H6 (chb03,
  one run): 4 of 7 seizures at 3.30 false/h, rejected.** No false detection
  occurred in the three seizure-free files.
* **Post hoc diagnosis (no change made).** The three missed seizures were
  found by line length but had fundamentals of 1.0-1.5 Hz, below the gate's
  floor. Fourier theory says why the floor sits there: a band-limited blink
  train peaks at 1.6 Hz (measured 1.5). Slow ictal delta and blinks occupy the
  same band, so the spectrum alone cannot separate them.

### T13. The tests had blind spots

Seventeen deliberate one-line bugs were run against the test suite; three
survived: a double filter pass (no test measured the output at the cutoff), a
biased wPLI² (indistinguishable under the null), and a random value in
`metrics.json`. Three tests were added; final run 17/17 caught.

### T14. Theory versus measurement (2026-10-18)

Eight probability models behind the decisions were tested against the
pipeline ([STATISTICAL_FOUNDATIONS](STATISTICAL_FOUNDATIONS.md)). Most matched
closely (wPLI bias to three decimals; least squares in log space as
efficient as maximum likelihood, 0.995). Two corrected our understanding:
* H1's peak-power noise is half sampling floor (predicted 0.038, a property
  of 3-minute recordings) and half estimator inefficiency (measured 0.057),
  caused by the window smearing peaks, not by the loss function;
* the first blink model used the nominal blink rate and over-predicted 3.5-30x;
  calibrated on the rate the detector actually sees, it matched within a
  factor of about 2.
* Power analysis: H6's 7 seizures gave a 42 % chance of passing even for a
  detector with exactly 60 % true sensitivity. A decisive test needs about
  76 seizures.

## Part 4. Changes that no bug forced

| driver | what changed | why it is better than the plan |
|---|---|---|
| data access | PhysioNet's site was unreachable; files came from its open-data mirror on AWS | identical files, proven by PhysioNet's own SHA-256 list |
| real-data format | CHB-MIT is a bipolar montage with a duplicated channel | montage detection; duplicate collapse; tested |
| hardware (8 GB laptop) | channel-by-channel filtering and spectra | measured 1.5 GB peak for 1 h × 32 channels |
| dependency risk | specparam is a release candidate | own fitter in the report path, specparam as test oracle (200/200 agreement) |
| privacy and cost | the LLM sees metrics only, never signal or identifiers | testable boundary (S-03, S-04) |
| scientific process | a test set used for development stops being a test | chb01 relabelled; H6 pre-registered on a new subject |
| repository hygiene | Dependabot built PRs on a stale branch; no protected `main` | `main` created from the first commit; feature branches and PRs |

## Part 5. Plan versus outcome

| component | plan | outcome | forced by |
|---|---|---|---|
| coupling measure | wPLI | debiased wPLI² | T1 |
| spectra | whole recording | outside detected events | T4 |
| detection band | broadband | 1-20 Hz | T2 |
| rhythm check | none | fundamental of the background-normalised spectrum, 2-7.5 Hz | T5, T8, T10 |
| z threshold / vote / duration / gap | 4 / 30 % / 8 s / 5 s | 2.5 / 1 channel / 10 s / 1 s | T3, T10, T11 (tuning rule) |
| synthetic benchmark | background + discharges + blinks + muscle | + alpha and spindle bursts, + event-free recordings | T9, T11 |
| tuning constraint | ≤ 1 false/h | ≤ 2 false/h (H2's limit) | T10 |
| real-data test | chb01 once | chb01 (development) + chb03 held out | T8 |
| checker rounding | inclusive ties | strict ties | T7 |

## Part 6. How we know the changes were right

Every change above was accepted only with one of these kinds of evidence:
1. **A before/after measurement on the same seeds**, so the change is the
   only difference (T2, T5, T10).
2. **A theory prediction confirmed by measurement**, so the change follows
   from a mechanism rather than a lucky setting (T1, T11, T12, T14).
3. **A held-out test committed before its data**, so the result cannot
   have been tuned towards (H6).
4. **A test that fails without the fix**, so the defect cannot return
   silently (T7, T13, every ISSUE's "verification" line).

Rejected results stay rejected. H1, H2, H3 (at 2 minutes), H5 and H6 are
reported as rejected, with the reason.

## Part 7. What the changes guarantee, and what they cannot

No change makes future failures impossible. What this project provides is
three layers that make failures expected, bounded and visible.

**1. Regression guarantee.** Every failure met during the build has a test
that fails if it returns:

| failure | test |
|---|---|
| causal or double filtering | `test_zero_phase_does_not_shift_an_impulse`, `test_applied_filter_is_minus_6_db_at_cutoff_not_minus_12` |
| wPLI bias | `test_debiased_wpli_is_unbiased_under_the_null`, `test_volume_conduction_inflates_plv_but_not_debiased_wpli` |
| events inside the spectrum | `test_excluded_windows_are_dropped` |
| muscle false alarms | `test_negative_control_rhythm_gate_removes_muscle_false_alarms` |
| harmonic read as rhythm | `test_rhythm_gate_reads_the_fundamental_not_a_harmonic` |
| rounding-tie escape | `test_precision_rule` |
| thresholds drifting from the tuning record | `test_config_thresholds_come_from_the_tuning_result` |
| nondeterministic output | `test_metrics_byte_identical_across_processes` |

Mutation testing (17/17) shows these tests catch the bugs they target.

**2. Known operating characteristics.** A user knows the expected
behaviour, with uncertainty: sensitivity 0.71-0.96 on synthetic data
depending on SNR; 4 of 7 seizures (Wilson [0.25, 0.84]) and 3.3 false/h
(upper bound 4.6/h) on held-out real data; known blind spots (slow delta
below 2 Hz, rhythms above 7.5 Hz, events shorter than 10 s).

**3. Production monitoring plan.** If the tool ran on real users' files,
these signals, all already in every `metrics.json`, would show it breaking
before anyone noticed a wrong conclusion:

| signal | why | action threshold |
|---|---|---|
| detections per hour on files reviewed as seizure-free | false alarms drifting up | above 4.6/h, the held-out upper bound: re-validate |
| share of detections with a fundamental within 0.5 Hz of the gate edges (2.0, 7.5 Hz) | the gate is being stressed by blinks or alpha | a rising share: inspect, consider the spatial blink cue |
| share of unreliable aperiodic fits (`aperiodic.n_poor_fits`) | recordings unlike the validated range | above about 10 % of channels: flag the report |
| bad-channel fraction and residual line noise | hardware or montage outside the validated range | outside validation ranges: flag the report |
| claim-checker rejections of LLM text | model drift after a provider update | any rise: fall back to the template and review |

## Part 8. Open questions this evidence points to

1. **A spatial cue for blinks** (frontal, symmetric) so the gate floor can
   drop below 2 Hz and recover slow ictal delta. Target: chb03's three misses.
2. **A duration model instead of hand-set rules.** The merge gap and minimum
   duration are crude duration priors; a hidden semi-Markov model fitted by
   expectation-maximisation would learn state durations from data.
3. **A window-aware spectral fit** (model the Hann kernel or use multitaper)
   to close the 1.5x gap between the peak-height estimator and its
   theoretical floor.
4. **A sized confirmatory test:** about 76 seizures and at least 12 hours of
   seizure-free recording, over several held-out CHB-MIT subjects.
