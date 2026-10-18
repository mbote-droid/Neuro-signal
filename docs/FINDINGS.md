# Findings

What validation discovered that the design did not anticipate, and what
each discovery changed. Numbers are from the result files listed in
[VALIDATION_REPORT.md](VALIDATION_REPORT.md); the story of each is in the
[build journal](BUILD_JOURNAL.md).

## Summary

| # | finding | changed |
|---|---|---|
| F-1 | plain wPLI is biased upwards with few epochs: 95th percentile 0.19 under pure volume conduction at 2 minutes | debiased wPLI² became the reported coupling measure |
| F-2 | H1's band-power half holds without exception, but its peak-power half fails because of measurement noise, not method bias | interpretation of peak power across short recordings |
| F-3 | the claim checker let one mutant through: a rounding tie | strict tie rule; the template never writes ties |
| F-4 | the claim checker cannot judge whether a cited key fits the sentence | documented limit of the contract |
| F-5 | the event detector rebuilt the H1 confound inside itself | rhythm gate on the background-normalised spectrum |
| F-6 | spike-wave harmonics, normal alpha/spindle bursts and blink trains each fooled the detector in turn; an easy synthetic benchmark hid all three | fundamental-frequency gate, realistic negatives, event-free recordings in tuning |
| F-7 | on held-out real data the frozen detector found 4 of 7 seizures at 3.3 false detections per hour (H6 rejected); no false detection occurred in seizure-free files | stated limits; the next step is not more tuning |
| F-8 | mutation testing found three code defects the tests could not see | three new tests |

## F-1 wPLI's small-sample bias (H3)

With six independent sources mixed into 19 sensors and no true coupling,
PLV exceeded 0.3 in 92 % of sensor pairs (median over 50 seeds), as
expected. But plain wPLI's 95th percentile was 0.193 at 120 s (60 epochs;
worst seed 0.275), failing the pre-registered 0.15; it fell to 0.095 at
600 s. The debiased squared estimator stayed at 0.021 (120 s) and 0.006
(600 s), and it still found a truly lagged pair (median 0.998).
**H3 as registered is rejected at 2 minutes and accepted at 10 minutes.**
The pipeline reports dwPLI as the coupling measure. Lesson: pre-register
the estimator, not only the measure.

## F-2 The aperiodic confound is real; peak power needs long recordings (H1)

When only the exponent steepened by 0.5, canonical 8-12 Hz band power fell
by a median of 68 % and changed by at least 30 % in **every** one of 200
cases, while the oscillation was unchanged. That half of H1 holds without
exception. The other half failed as registered: the fitted alpha peak power
stayed within 0.05 log10 in only 60.5 % of cases (median absolute change
0.038, 90th percentile 0.139). A secondary paired analysis, with the same
noise realisation in both conditions, puts the method's own bias at 0.0012
log10 (99 % within 0.05). So the shortfall is sampling noise between two
separate 3-minute recordings, not a defect of the parameterisation. A
sensitivity analysis rotating the spectrum about 20 Hz instead of 1 Hz
*raised* band power by a median of 44 %: band-power changes can take either
sign from an exponent change alone. **H1 rejected as registered.** The
practical reading: peak-power differences below about 0.1 log10 between two
short recordings are within noise.

## F-3 and F-4 What the claim checker can and cannot do (H4)

First full run: 2152 of 2153 live mutants caught. The escape wrote "1"
while citing a metric equal to 0.5; the checker accepted the tie
(|1 - 0.5| = 0.5 ≤ 0.5), the independent oracle (round half to even) did
not. Both now use a strict rule, and the template adds a decimal instead of
writing a tie. Re-run: **2152 of 2152 live mutants caught across nine
operators, 60 of 60 faithful explanations accepted** (miss-rate 95 % upper
bound 0.0014 by the rule of three; H4 accepted on the second run, rejected
on the first). The explanation template's wording was revised for v0.1.0
(singular/plural counts, clearer line-noise sentence); the checker campaign
was re-run on the new text: 2157 of 2157 live mutants caught (3 equivalent,
previously 8), 60 of 60 faithful accepted, same conclusion.

Two limits remain and are stated in the report:
* the same mutant cited `processing.1.highpass_hz` for a channel count: the
  checker verifies that every number traces to a computed value at the
  written precision, not that the key fits the sentence. Mutants that
  swapped keys with numerically equal values (3 in the latest run) are
  counted as equivalent, but they are semantically wrong text;
* numbers written as words are invisible (60 of 60 "number as words"
  mutants passed). The template and the LLM prompt write digits only.

## F-5 The detector rebuilt the H1 confound (H5)

The first detector gated events on the dominant frequency of their raw
spectrum. Synthetic discharges were strong enough to dominate it. Real EEG
is not: all seven chb01 seizures passed the line-length stage, but their
raw spectra peaked at 1-2 Hz because of the 1/f background, so the gate
discarded five. **H5 rejected (2 of 7 at 0.52 false detections per
hour).** Dividing the event spectrum by the background spectrum of the same
channels recovers the rhythm (2.5-3.5 Hz for five of the seven seizures).
chb01 became a development set; a held-out test was pre-registered.

## F-6 Three ways an easy benchmark lies

Each fix exposed the next problem, and each was invisible until the
synthetic data contained the right negative:

1. **Harmonics.** Normalising by a 1/f background boosts a spike-wave
   train's harmonics above its fundamental; the gate now reads the lowest
   strong peak (the fundamental).
2. **Normal rhythms.** Posterior alpha bursts and spindles rise above a
   recording's own baseline. On chb01 they caused most of 51 false
   detections; adding them to the generator made the first tuning
   constraint (≤ 1 false/h) infeasible, and the tuning rule then chose a
   delta-theta gate (2-7.5 Hz).
3. **Blink trains.** A blink band-limited to 1-20 Hz is a 2.5 Hz wave;
   consecutive blinks merged across a 5 s gap became one "rhythmic event".
   The tuning set hid it because every tuning recording contained real
   events. Event-free recordings now make up one in five, and the merge gap
   is tuned (1 s selected).

Cost of realism: on the final, harder synthetic benchmark the detector
reaches sensitivity 0.847 (Wilson [0.803, 0.882]) at 1.68 false detections
per hour; **H2 is rejected** (it was accepted, 0.955 at 0.69/h, on the
earlier benchmark without normal-rhythm bursts or event-free recordings).
Sensitivity is 0.95-0.96 at 6-10 dB and 0.71-0.76 at 0-3 dB.

## F-7 Held-out real data (H6)

The frozen detector was committed before chb03 was downloaded and run once:
**4 of 7 seizures (57 %, Wilson [0.25, 0.84]) at 3.30 false detections per
hour (95 % upper bound 4.6/h). H6 rejected** on both criteria. Two
observations for the next iteration, not acted on here:
* the three seizure-free files produced no false detection at all; every
  false detection fell in a file that contains a seizure, several within
  minutes of it, which suggests peri-ictal rhythmic activity rather than
  artifact;
* all three missed seizures *were* found by the line-length stage (peak z
  5.8-12.2); the rhythm gate rejected them because their fundamental was
  1.0-1.5 Hz, below its 2 Hz floor (post hoc diagnosis, no change made).
  chb03's seizures include slow delta rhythms that the gate's lower limit,
  set to reject blinks and drift, also rejects. Lowering it would re-admit
  the blink trains of F-6; telling the two apart needs a spatial cue
  (blinks are frontal and symmetric), which is the next design step.

On chb01, now a development set, the same detector finds 6 of 7 at 1.66/h;
that number is optimistic by construction and is not a test result.

A per-recording, unsupervised line-length detector with fixed thresholds is
a weak seizure detector; published patient-specific detectors on CHB-MIT
report far higher sensitivity. The value of this component is the
evidence trail, not the detector: every number is reproducible, and every
change was forced by a measured failure.

## F-8 The tests had blind spots (mutation testing)

Seventeen one-line code mutants were run against the test suite. Three
survived the first run:
* a forward-backward (`filtfilt`-style) second pass: no test measured the
  filter's *output* at the cutoff (only its design); a new test checks
  -6 dB, not -12 dB, at the cutoff;
* replacing debiased wPLI² by plain wPLI²: both are small under the null;
  a new test checks that the debiased estimator goes negative and averages
  near zero;
* a nondeterministic value in `metrics.json`: the first mutant used a Unix
  timestamp, which rounding to 6 significant digits made identical across
  quick runs (an equivalent mutant); replaced by a random run id, which the
  determinism test catches.

Final run: **17 of 17 mutants killed.**
