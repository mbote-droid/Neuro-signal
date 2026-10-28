---
title: "Validation-first EEG pipelines: how synthetic benchmarks mislead, and how pre-registration catches it"
author: "Samuel Ngigi Mbote"
date: "Version 2, October 2026"
---

<!--
Version 2: adds the pre-registered evaluation of language-model explainers (H7), an outside
report and a deliberate bug hunt. Software DOI (all versions): 10.5281/zenodo.23447346.
Every number below is taken from results/validation/*.json; see docs/VALIDATION_REPORT.md.
H7c results are from results/validation/llm_audit.json.
-->

::: {.affil}
Independent Researcher, Nairobi, Kenya\
ORCID [0009-0003-2319-8873](https://orcid.org/0009-0003-2319-8873) ·
<mbotesamuel9@gmail.com>
:::

## Abstract

Automated EEG analysis pipelines are usually developed and evaluated on the
same synthetic or public data, and the outcome measures are chosen after
the results are known. We built an open, deterministic scalp-EEG pipeline
(quality control, zero-phase filtering, aperiodic/periodic spectral
parameterisation, debiased weighted phase-lag index, an unsupervised
rhythmic-event detector and a citation-checked plain-language summary) under
a validation-first protocol: six hypotheses with numeric pass thresholds
were committed to version control before the code or the data they concern
existed, every method was tested against synthetic ground truth, and the
test suite and the explanation checker were themselves mutation-tested.
Four of the first six hypotheses were rejected. The protocol's value lay in how
they failed. A synthetic detection benchmark on which the detector passed
(sensitivity 0.955 at 0.69 false detections per hour) hid four failure
modes that only appeared on real recordings or on deliberately harder
synthetic negatives: a rhythm gate fooled by the 1/f background (the very
confound one hypothesis was written to test), harmonics of spike-wave
discharges, normal alpha and spindle bursts, and blink trains merged into
"rhythms". On a harder benchmark the detector fell to 0.847 [95 % CI
0.803-0.882] at 1.68 false detections per hour, and on a pre-registered
held-out subject of the CHB-MIT database it found 4 of 7 seizures at 3.3
false detections per hour. The pre-registered estimator thresholds also
exposed the small-sample bias of plain wPLI (95th percentile 0.19 under
pure volume conduction at two minutes). A seventh, pre-registered
hypothesis tested language models as explainers under a citation contract
checked mechanically: a free cloud model (gemini-3.8-flash) was accepted on
30 of 30 recordings after at most one repair, and a small local model
(qwen2.5:3b) on 0 of 30, every faulty reply being caught and replaced. A
blinded audit of 20 accepted cloud explanations found 3 that were
misleading although every number in them was correct, above the
registered limit of 2. The
checker's own error model proved incomplete in the same way as the
detector's benchmark: an outside report and a deliberate bug hunt found
sign flips and invisible characters that the original checker passed (it
caught 2625 of 3334 mutated explanations; the corrected one, all 3334). We
argue that, for methods papers, the benchmark and the error model are both
researcher degrees of freedom, and we give a short, checkable protocol to
constrain them. Code, data-retrieval scripts with
checksums and all result files: https://doi.org/10.5281/zenodo.23447346.

**Keywords:** EEG, validation, pre-registration, synthetic data, aperiodic
activity, phase-lag index, seizure detection, reproducibility, mutation
testing

## 1. Introduction

The same EEG recording analysed by different teams gives different answers
(Trübutschek et al. 2024), and preprocessing choices alone change
downstream results (Robbins et al. 2020). Methods papers usually respond with
a new pipeline and a benchmark on which it performs well. The benchmark is
rarely fixed before the method is tuned, and when it is synthetic, it
contains exactly the phenomena its author thought of. Leakage between
development and evaluation data is a known source of irreproducible
results in machine-learning-based science (Kapoor and Narayanan 2023), and
pre-registration is the standard remedy in empirical research (Nosek et al.
2018). Neither practice is routine in signal-processing methods work, where
the "experiment" is a simulation the author designs.

This paper reports what happened when an EEG pipeline was built under a
validation-first protocol, and treats the pipeline mainly as the case
study. Three well-documented interpretation errors motivated it: a change
in canonical band power read as a change in an oscillation when only the
aperiodic (1/f) exponent moved (Donoghue et al. 2020); volume conduction
read as connectivity (Nolte et al. 2004; Vinck et al. 2011); and, newer,
plain-language summaries that state numbers nobody computed. For each, a
hypothesis with a numeric threshold was written down first, and for the
event detector, two more tested whether synthetic validation transfers to
real data.

Our contributions are:

1. an account of how a synthetic benchmark misled the development of an
   event detector four times, and which protocol element exposed each
   failure (Section 3.2);
2. evidence that pre-registering the *estimator*, not only the measure,
   matters, from the small-sample bias of wPLI (Section 3.3);
3. a citation contract for generated explanations, a mutation-testing
   evaluation of the checker that enforces it, and evidence that the
   checker's error model, like a benchmark, encodes its author's blind spots
   (Sections 3.5 and 3.8);
4. a pre-registered evaluation of a cloud and a small local language model
   writing under that contract (Section 3.7);
5. a short protocol for validation-first methods work that a reviewer can
   check from a repository (Section 4.1).

## 2. Methods

### 2.1 Pipeline

The pipeline reads EDF/EDF+, BDF or BrainVision files through MNE-Python,
refuses oversize or unsupported files before parsing, converts to
microvolts and drops identifying header fields. Flat channels are marked on
the raw data; the signal is then filtered with a Hamming-window FIR design
applied in a single pass with delay compensation (zero phase, magnitude
response H rather than the H² of forward-backward filtering; Widmann et al.
2015): a 50 Hz notch with harmonics and a 0.5-45 Hz band-pass. Noisy and
low-amplitude channels are marked with median/MAD statistics, and
referential montages are re-referenced to the common average of good
channels (bipolar montages are left unchanged).

Events are detected before spectra are estimated, so that spectra and
coupling describe the background. The detector computes line length
(Esteller et al. 2001) on the 1-20 Hz band in 2 s windows (1 s step), converts it to
a robust z-score per channel (median/MAD over the recording), requires a
fraction of channels to exceed a threshold, keeps runs of at least a
minimum duration, merges runs separated by less than a gap, and finally
gates each candidate on the fundamental frequency of its spectrum divided
by the background spectrum of the same channels. All five thresholds were
chosen by grid search on synthetic tuning seeds only (Section 2.3).

Spectra are Welch estimates (2 s Hann windows, 50 % overlap) excluding
event windows. The aperiodic and periodic components are separated with a
specparam-style model (Donoghue et al. 2020): a robust line in log-log
space, greedy Gaussian peak detection and a joint bounded least-squares
fit; specparam itself is used only as a test oracle. Fits with R² below 0.8
or an exponent outside [0, 4] are listed and excluded from averages. Phase
coupling is reported as the debiased squared weighted phase-lag index
(dwPLI; Vinck et al. 2011), with the phase-locking value (PLV) shown only
as a contrast.

The output is a JSON file of metrics that is byte-identical across runs, a
set of figures, and an HTML report with a plain-language explanation
(Section 2.5).

### 2.2 Pre-registration

Hypotheses H1-H5 were committed to the repository before the code that
tests them (commit `1d92eb4`, 26 minutes before the first code commit).
H6 was committed after H5 failed and before any file of its test subject
was downloaded (`ed41812`); the detector was frozen in a later commit
(`36b7964`) and run once on that subject. Each hypothesis states the data,
the measure and the numeric threshold:

| | hypothesis | pass condition |
|---|---|---|
| H1 | aperiodic confound | exponent +0.5, alpha unchanged: 8-12 Hz band power changes ≥ 30 % in ≥ 95 % of cases, and fitted alpha peak power changes ≤ 0.05 log10 in ≥ 90 % |
| H2 | synthetic detection | 3 Hz spike-wave at ≥ 0 dB SNR: sensitivity ≥ 0.90, Wilson lower bound ≥ 0.80, ≤ 2 false detections/h |
| H3 | volume conduction | independent sources mixed into 19 sensors: PLV > 0.3 in ≥ 50 % of pairs; wPLI 95th percentile ≤ 0.15; a truly lagged pair has wPLI > 0.5 |
| H4 | explanation faithfulness | checker rejects every live mutant (≥ 300 from ≥ 6 operators) and accepts every faithful explanation |
| H5 | transfer (exploratory) | CHB-MIT chb01: ≥ 5 of 7 seizures at ≤ 2 false/h, thresholds from synthetic data only |
| H6 | held-out subject | CHB-MIT chb03, frozen detector, one run: ≥ 60 % of seizures at ≤ 2 false/h |
| H7a | cloud language model as explainer | ≥ 24 of 30 explanations accepted by the checker after at most one repair |
| H7b | small local model (exploratory) | acceptance reported with Wilson intervals; no threshold |
| H7c | blinded audit of accepted text | ≤ 2 of 20 audited cloud-model explanations contain a false or misleading statement |

A rejected hypothesis is reported as rejected; changes made after a result
are described as exploratory and, where they affected a later test, that
test was re-registered on new data. One deviation is recorded: the tuning
rule's false-detection constraint was relaxed from 1 to 2 per hour, H2's
own limit, after no grid point met it; the infeasible grid is kept as a
result file. H7 was registered after release v0.1.1 and before any model
call (`821682b`); the two models were recorded before the runs (`3878ea7`).
When an outside report later showed a checker defect (Section 3.8), an
amendment kept H7's primary verdicts on the checker as registered, frozen
as a hash-pinned copy, and added the corrected checker as a secondary
analysis of the same saved replies.

### 2.3 Synthetic ground truth

Recordings are generated with a 19-channel 10-20 layout at 256 Hz. Each
channel's background is shaped noise with a random aperiodic exponent and
offset and an optional alpha peak; flat and noisy channels, 50 Hz mains
interference, blinks (frontal, about 15 per minute), muscle bursts,
posterior alpha bursts and spindles can be added. Events are 3 Hz
spike-wave trains with a small frequency glide, injected into a random
subset of channels at a set SNR (0, 3, 6 or 10 dB). For H3, independent
sources are mixed into sensors through a random lead field, with and
without one truly lagged source pair. The generator writes the ground truth
to a separate file that the pipeline never reads.

Tuning seeds (0-59) and evaluation seeds (1000-1199) are disjoint. In the
final benchmark one recording in five contains no events. The benchmark
evolved during development (Section 3.2); every version is in the
repository history.

### 2.4 Real data

The CHB-MIT Scalp EEG Database v1.0.0 (Shoeb 2009; Goldberger et al.
2000), paediatric recordings in a bipolar montage at 256 Hz, was retrieved
from PhysioNet's open-data mirror with SHA-256 verification. A
pre-registered file rule selected, for each subject, every file with at
least one seizure plus the first three seizure-free files. Subject chb01
(7 seizures, 9.6 h) was the H5 test and then became a development set;
subject chb03 (7 seizures, 10 h) was the held-out H6 test. Detections were
scored with the any-overlap rule (Ziyabari et al. 2017); false detections
per hour are reported with a Poisson upper bound.

### 2.5 Explanations and the claim checker

The plain-language summary is written either by a deterministic template
or, optionally, by a large language model that receives only the metrics.
In both cases every number must carry a citation to the metric it comes
from, written `value [[metric.key]]`. A checker that contains no model
parses the text with regular expressions and rejects it if a cited key does
not exist, a written value does not round to the cited metric at its
written precision (with a strict rule at exact ties), a number has no
citation, a channel name is not in the recording, diagnostic vocabulary
appears, or the research-use notice is missing. Rejected text is replaced
by the template and the failure is shown in the report.

The checker was evaluated by mutation (H4): first nine operators (perturb a
number, scale it by 1000, swap a citation for another key, cite a
non-existent key, add an uncited number, invent a channel, add a
diagnosis, drop the notice, and drop a citation), later fourteen (a sign
flip written with a typographic minus, a sign flip inside bold markup, two
numbers trading citations, a zero-width character that adds a decimal, and
an uncited number with a leading decimal point; Section 3.8), each applied
four times to 60 faithful explanations of varied synthetic recordings. A mutant whose text is still true at the
written precision is "equivalent" and excluded; equivalence is decided
from the metric values by integer rounding, independently of the checker.
The same principle, validating the validator with realistic wrong answers
and mutation testing, was applied earlier to automated graders for AI
agents on biomedical engineering tasks (Mbote 2026).

Language models were evaluated as explainers in H7 on 30 further synthetic
recordings (seeds disjoint from H4's), with the system prompt of the
released explainer (pinned by hash), temperature 0 and at most one repair
round in which the checker's findings are returned to the model. The cloud
model was gemini-3.8-flash on Google's free API tier; the local model was
qwen2.5:3b (4-bit, 1.9 GB, served by Ollama on the 8 GB laptop). Every reply
was saved before it was checked, so runs interrupted by the free tier's
daily quota resumed without repeating a call. Up to 20 accepted
explanations per model were sampled for a blinded audit by the author,
who judged each for statements false or misleading given the metrics they
cite: the semantic errors the checker cannot see.

### 2.6 Testing the tests

Beyond unit, property-based (linearity, time-shift equivariance),
metamorphic (Parseval), differential (specparam) and ground-truth tests,
one-line code mutants (seventeen at release, twenty-three after the bug
hunt; for example, a causal filter, a forward-backward second pass, plain
instead of debiased wPLI², a nondeterministic value in the output) were run
against the test suite; a surviving mutant marks a blind spot. Before this
version, a deliberate bug hunt added property-based fuzzing of the checker
(arbitrary Unicode, number forms) and of the file readers (truncated,
damaged and lying files), edge-case recordings, an independent read-only
code review, and synthetic artifacts built to imitate rhythmic events
(chewing, electrode pops, eye flutter, sweat drift; exploratory).

### 2.7 Statistics and theory checks

Proportions carry Wilson 95 % intervals, zero-failure rates the rule of
three, and false-detection rates a Wilson-Hilferty Poisson upper bound.
Where a decision rested on a statistical model, the model's prediction was
compared with the measurement: the Welch sampling distribution for H1, the
null distribution of the imaginary cross-spectrum for wPLI bias, Whittle
maximum likelihood for the log-space fit, the Fourier transform of a blink
train for the gate floor, a Poisson process for blink merging, a
contamination model for robust z-scores, and binomial power for H6.

All computation ran on one CPU core of a laptop with 8 GB of RAM; a
one-hour, 32-channel recording is processed in 12.7 s with 1.5 GB peak
memory.

## 3. Results

### 3.1 Confirmatory outcomes

| | result | verdict |
|---|---|---|
| H1 | band power changed ≥ 30 % in 200/200 cases (median −68 %); peak power within 0.05 log10 in 60.5 % | rejected |
| H2 | sensitivity 0.847 [0.803, 0.882] (271/320 events), 1.68 false/h (56 in 33.3 h) | rejected |
| H3 | PLV > 0.3 in 92 % of pairs; wPLI p95 0.193 at 2 min, 0.095 at 10 min; lagged pair 0.998 | rejected at 2 min, accepted at 10 min |
| H4 | 3334/3334 live mutants rejected (fourteen operators), 60/60 faithful accepted | accepted (rejected on the first run) |
| H5 | 2/7 seizures, 0.52 false/h | rejected |
| H6 | 4/7 seizures (Wilson [0.25, 0.84]), 3.30 false/h (upper bound 4.6) | rejected |
| H7a | gemini-3.8-flash: 30/30 accepted after at most one repair (24/30 first time) | accepted |
| H7b | qwen2.5:3b: 0/30 accepted (Wilson [0.00, 0.11]); all 30 replaced by the template | exploratory |
| H7c | 3/20 audited cloud explanations misleading (Wilson [0.05, 0.36]); all three attach a correct number to the wrong concept | rejected |

Engineering requirements were met: aperiodic exponent median absolute error
0.014 on 200 synthetic spectra, agreement with specparam in 200/200,
alpha peak frequency error 0.067 Hz, and perfect recall and precision for
bad channels on 100 recordings.

### 3.2 How the synthetic benchmark misled

The detector's development is a sequence of four failures, each invisible
to the benchmark of the moment.

**The 1/f trap, rebuilt inside the detector.** The first detector gated
candidates on the dominant frequency of their raw spectrum. Synthetic
discharges were strong enough to dominate it; it passed the synthetic
benchmark. On chb01 all seven seizures passed the line-length stage, but
the raw spectra of real EEG peak at 1-2 Hz because of the aperiodic
background, so the gate rejected five (H5 rejected, 2/7). This is the
confound H1 was written to test, reproduced in our own code. Dividing the
event spectrum by the background spectrum of the same channels recovered
the rhythm (2.5-3.5 Hz in five of seven seizures). Because chb01 had now
informed a design change, it became a development set and a new held-out
test (H6) was registered on a subject not yet downloaded.

**Normal rhythms.** With the normalised gate, chb01 gave 5/7 seizures but
51 false detections (5.3/h), most at 8-13 Hz: posterior alpha bursts and
spindles, which rise above a recording's own background exactly as
seizures do. The benchmark contained no such bursts. They were added to the
generator first, so that the synthetic tuning rule, not chb01, chose the
response: a delta-theta gate.

**Harmonics.** With normal rhythms in the benchmark, no grid point met the
tuning constraint. Listing every candidate showed that dividing by a 1/f
background lifts a spike-wave train's harmonics above its fundamental; the
gate now reads the lowest peak at least half the size of the largest.

**Blink trains.** On event-free recordings the detector made 6.4-6.6 false
detections per hour at every threshold. A blink band-limited to 1-20 Hz is
a wave of about 2 Hz, and at 15 blinks per minute a 5 s merge gap joined
consecutive blinks into long "rhythmic" events. The benchmark hid this
because every tuning recording contained real events, which raised the
robust baseline. A Poisson model of supra-threshold blinks predicts 13.7
long merged runs per hour at a 5 s gap and 0.07 at 1 s (measured 21.9 and
0.3). One recording in five is now event-free and the gap is tuned.

The cost of realism was measured on the same detector family: the first
campaign accepted H2 on the earlier benchmark (sensitivity 0.955 at
0.69/h; result file at commit `19198f7`), and the final campaign rejected
it (0.847 at 1.68/h; 0.95-0.96 at 6-10 dB, 0.71-0.76 at 0-3 dB). We
report the final run as the verdict because the earlier benchmark lacked
negatives known to occur in real EEG; both runs are in the repository.
On held-out chb03 the frozen detector found 4 of 7 seizures at 3.30/h
(H6 rejected). The three seizure-free files produced no false detection;
every false detection fell in a file containing a seizure. All three missed
seizures exceeded the line-length threshold (peak z 5.8-12.2) but had
fundamentals of 1.0-1.5 Hz, below the gate's 2 Hz floor, a floor that
exists to reject blinks (post hoc diagnosis; no change made). On chb01,
now a development set, the same detector finds 6/7 at 1.66/h, a number
that is optimistic by construction.

### 3.3 Pre-register the estimator, not only the measure

Under pure volume conduction (six independent sources, no coupling), PLV
exceeded 0.3 in 92 % of sensor pairs, as expected. Plain wPLI, the measure
named in H3, had a 95th percentile of 0.193 with two minutes of data (60
epochs), above the registered 0.15, and 0.095 with ten minutes. The bias is
predicted by the null distribution of the imaginary cross-spectrum:
expected wPLI 0.1457 at 60 epochs (measured 0.1455) and 0.0651 at 300
(measured 0.0655). The debiased estimator stayed at 0.021 and 0.006 and
still detected a truly lagged pair (median 0.998). H3 is rejected at two
minutes as registered; the pipeline reports dwPLI.

### 3.4 The aperiodic confound holds; the registered tolerance did not

When only the aperiodic exponent rose by 0.5, 8-12 Hz band power fell by a
median of 68 % and changed by at least 30 % in all 200 cases, with the
oscillation unchanged; rotating about 20 Hz instead of 1 Hz raised band
power by a median of 44 %, so the sign of a band-power change is not
informative either. Fitted peak power, however, stayed within 0.05 log10 in
only 60.5 % of cases. A paired analysis (same noise realisation in both
conditions) puts the method's bias at 0.0012 log10. The Welch sampling
distribution predicts a per-bin log-power noise of 0.0334 (measured 0.033)
and a peak-height difference SD of 0.038 for an efficient estimator; the
measured SD was 0.057, so the estimator runs about 1.5 times above the
sampling floor. H1's tolerance was tighter than two separate three-minute
recordings allow. It was a design error in the hypothesis, recorded as a
rejection rather than corrected after the fact.

### 3.5 The claim checker

On its first full run the checker caught 2152 of 2153 live mutants. The
escape wrote "1" while citing a metric equal to 0.5: the checker accepted
the tie, and the independent equivalence oracle (round half to even) did
not. Both now use a strict rule, and the template adds a decimal rather
than write a tie. After the fix, 2152/2152 were rejected, and after a later
revision of the template wording 2157/2157, with 60/60 faithful
explanations accepted. With the fourteen operators of Section 3.8 the
current checker rejects 3334/3334 (26 equivalent; miss-rate upper bound
0.0009), while the checker as first released rejects 2625: it misses every
typographic-minus, zero-width and leading-dot mutant. Two limits remain. The checker
verifies that each number traces to a computed value, not that the cited
key fits the sentence: a channel count citing a filter cutoff of the same
value passes. And numbers written as words are outside the contract (60/60
such mutants passed). These are stated in every report.

### 3.6 The test suite's blind spots

Three of seventeen code mutants survived the first run: a forward-backward
second filter pass (no test measured the output at the cutoff), plain
instead of debiased wPLI² (both are small under the null), and a
timestamp in the output that rounding made identical across quick runs.
Each led to a new test; the run at release killed 17 of 17, and with one
mutant undoing each later fix, 23 of 23.

### 3.7 Language models under the citation contract (H7)

| | gemini-3.8-flash (cloud) | qwen2.5:3b (local) |
|---|---|---|
| accepted at the first attempt | 24/30 [0.63, 0.90] | 0/30 [0.00, 0.11] |
| accepted after at most one repair | 30/30 [0.89, 1.00] | 0/30 [0.00, 0.11] |
| first-attempt findings | uncited numbers 14, value mismatch 2 (scientific notation split), unknown channel 2, missing value 1 | uncited numbers 709, missing notice 21, unknown channel 21, diagnostic word 1 |
| median seconds per call | 106 | 307 |

The cloud model met the registered threshold (H7a). None of its six
rejected first replies stated a wrong value; every finding came from
format: LaTeX notation ("R^2", "µV^2") whose exponent the checker counts as
an uncited number (three replies), correct values in scientific notation
that the registered checker split into two numbers (two), replies cut off
mid-sentence (two), a channel pair written as "C3-P7" and read as an
unknown bipolar channel (one), and an incompletely stated channel list
(one). Each was repaired in one round. The small local model never satisfied the contract: its replies
averaged about 23 uncited numbers, and repair did not help (728 uncited
numbers in the second attempts). Every one of its 30 explanations was
therefore replaced by the deterministic template, which is the behaviour
the design intends: no faulty text reached a report. The corrected
checker (Section 3.8) changed no verdict: none of the 96 replies wrote a
typographic minus, a zero-width character or a leading-dot number.

The blinded audit (H7c) rejected the hypothesis: 3 of 20 accepted cloud
explanations contained a misleading statement (Wilson [0.05, 0.36]), above
the registered limit of 2. All three had the same shape: a correct number,
correctly cited, attached to the wrong concept. Twice the count of channels
with an alpha peak was presented as the number of clean channels or as the
coverage of the aperiodic fit ("robust aperiodic fitting across 18
channels"); the counts coincide when every good channel has an alpha peak,
so the value matched and the checker accepted it. Once the detector's
line-length z-score was called a "peak amplitude statistic". No audited
explanation invented a finding, misread PLV as evidence of coupling or
used diagnostic language. The checker verifies that a number equals the
metric it cites, not that the metric is the one the sentence is about;
this is the residual error it leaves to a reader. Because the local model
had no accepted explanation, all audited items came from the cloud model,
and hiding the model had no effect.

### 3.8 The error model is a researcher degree of freedom too

After release, an outside reader reported that the checker read
"−0.30 [[key]]", written with a typographic minus, as 0.30: a sign flip
passed as traced. The mutation set had only ever written ASCII hyphens, so
the gap lay outside everything H4 had tested. A deliberate bug hunt then
found three more ways a wrong number could pass (a zero-width character
inside a number, which displays 1.500 while the checker read 1; a number
with a leading decimal point, which was invisible; and a minus inside bold
markup, a regression introduced by the first fix and caught by the
independent review), as well as defects outside the checker: damaged files
crashing instead of being refused, a flat recording start measured twice,
and a montage decision that one ECG channel could overturn. Each finding
has a regression test and a mutant that undoes it; the H2, H4 (template),
H5 and H6 results and the quality-control validation were re-run and are
unchanged. Synthetic artifacts built to imitate rhythmic events exposed a
new weakness of the detector: chewing at 1-3 Hz on temporal channels
raised false detections from 2.40 to 6.00 per hour on event-free
recordings (16 of 60 episodes reported; exploratory), while eye flutter
(4 of 60), electrode pops (1 of 63) and sweat drift (none) did little.

## 4. Discussion

The detector is not the contribution. A per-recording, unsupervised
line-length detector with fixed thresholds is weak; patient-specific
detectors on CHB-MIT report far higher sensitivity (Shoeb 2009). What the
protocol produced is an evidence trail in which every failure was found,
dated, explained and kept.

Three observations generalise. First, a synthetic benchmark is a
hypothesis about what matters, and it encodes the developer's blind spots:
each of the four detector failures was absent from the benchmark until a
real recording or a deliberately adversarial negative revealed it, and the
headline sensitivity fell from 0.955 to 0.847 as the benchmark became more
realistic. The benchmark is therefore a researcher degree of freedom in the
same sense as an analysis choice, and its versions should be reported.
Second, pre-registration did not prevent mistakes; it made them
unambiguous. Without a committed threshold, the wPLI bias and the H1
tolerance would have read as "acceptable" results, and the chb01 numbers
after redesign (6/7) would have been reported as a test. Third, the
cheapest controls caught the most: event-free recordings, a held-out subject
named before download, and mutants of the tests themselves. Fourth, the
same holds one level up: a mutation set is a hypothesis about how text can
be wrong, and the checker passed every error its author had imagined while
missing 709 of 3334 that an outside reader and a deliberate search
supplied. Validation of a validator is only as complete as its error
model, which should be versioned and reported like a benchmark.

The language-model results support a narrow conclusion. A capable cloud
model can follow a citation contract almost unaided, and a small local
model cannot; in both cases the mechanical checker decided what a reader
saw, so the small model's failures cost fluency, not correctness. Accepted text
was not always right in meaning: 3 of 20 audited explanations labelled a
correct number with the wrong concept, which a value check cannot see.
Constraining which metrics a sentence may cite, for example by section, is
a mechanical step towards closing that gap.

### 4.1 A checkable protocol

We suggest the following minimum for methods papers whose evaluation is
partly synthetic. Each item can be verified from a repository.

1. Hypotheses with numeric thresholds, naming the estimator, committed
   before the code and data they concern.
2. Disjoint tuning and evaluation seeds; the benchmark's generator and every
   version of it in version control.
3. Negatives the method is likely to confuse with its target, and records
   with no target at all.
4. A real-data subject held out and named before download; any subject that
   informed a design change relabelled as development.
5. Theory-based predictions for the key estimators, compared with
   simulation.
6. Mutation testing of the test suite and of any automated checker, with
   the error model versioned, extended by fuzzing, and open to outside
   reports.
7. Rejected hypotheses reported as rejected; deviations listed.

### 4.2 Limitations

Pre-registration here relied on commit history in the same repository,
which a determined author could rewrite; an external registry such as OSF
would be stronger and is planned for the next round. The work was done by
one person over a short period, so decisions were not independently
reviewed. The real-data base is small (two paediatric subjects, about 20 hours,
14 seizures, one used for development). With seven seizures, H6 was close
to a coin flip by design: a detector with true sensitivity 0.60 passes its
rule with probability 0.42. Showing a lower bound above 0.6 with 80 % power
would take about 76 seizures if the true sensitivity were 0.75. The
synthetic generator lacks sleep stages, interictal spikes and evolving
ictal frequency content, and chewing remains a source of false detections.
Non-EEG channels such as ECG are excluded from the montage decision and the
average reference but still enter spectra and the detector's channel vote.
H7 used two models, one run each, at temperature 0, on synthetic metrics
only; its audit was done by a single rater, the tool's author, not an
independent one, who read the items with a guide giving the same fixed
description of each metric under every sentence.
The tool is for research use only and is not a medical device.

### 4.3 Future work

A spatial cue to separate frontal, symmetric blinks from slow ictal delta,
which would allow a lower gate floor, and an EMG cue against chewing; a
confirmatory test sized by the power analysis on further CHB-MIT subjects,
pre-registered externally; a local model used to generate realistic,
subtly wrong explanations, to measure the checker's semantic blind spot at
scale; section-scoped citation rules aimed at the error H7c found; and a language-model judge evaluated against the human audit.

## 5. Conclusion

Building an EEG pipeline against pre-registered thresholds rejected four of
six hypotheses and exposed four failures that a synthetic benchmark had
hidden, including the exact confound the project was designed to avoid. The
checker that guards its language-model explanations showed the same
pattern one level up, and real models showed why it matters: the one that
broke the contract every time never reached a reader.
None of these would have been visible in a conventional benchmark-and-report
workflow. Validation-first development costs little computation and makes
methods results harder to overstate.

## Data and code availability

Source code, the synthetic generators, the data-retrieval script with
checksums, every result file with provenance and a SHA-256 manifest, and
the build journal are archived at https://doi.org/10.5281/zenodo.23447346 (MIT licence;
version 1 of this preprint used release v0.1.1, version 2 release v0.1.2, doi:10.5281/zenodo.23716723, which adds H7 and
the bug hunt) and developed at https://github.com/mbote-droid/Neuro-signal.
CHB-MIT is available from PhysioNet under the Open Data Commons Attribution
License v1.0.

<!-- Acknowledgements: thank the GitHub user who reported issue #21, once they have said how they
wish to be named. -->

## Funding

This research received no specific grant from any funding agency in the
public, commercial, or not-for-profit sectors.

## Competing interests

The author declares no competing interests.

## References

Donoghue T, Haller M, Peterson EJ, et al. (2020) Parameterizing neural
power spectra into periodic and aperiodic components. *Nature Neuroscience*
23:1655-1665.

Esteller R, Echauz J, Tcheng T, Litt B, Pless B (2001) Line length: an
efficient feature for seizure onset detection. *Proceedings of the 23rd
Annual International Conference of the IEEE EMBS*.

Goldberger AL, Amaral LAN, Glass L, et al. (2000) PhysioBank,
PhysioToolkit, and PhysioNet. *Circulation* 101:e215-e220.

Kapoor S, Narayanan A (2023) Leakage and the reproducibility crisis in
machine-learning-based science. *Patterns* 4:100804.

Mbote SN (2026) Validating the graders: physics-aware rewards for AI agents
on biomedical engineering tasks. Preprint, Zenodo.
https://doi.org/10.5281/zenodo.23309911

Nolte G, Bai O, Wheaton L, et al. (2004) Identifying true brain interaction
from EEG data using the imaginary part of coherency. *Clinical
Neurophysiology* 115:2292-2307.

Nosek BA, Ebersole CR, DeHaven AC, Mellor DT (2018) The preregistration
revolution. *Proceedings of the National Academy of Sciences* 115:2600-2606.

Robbins KA, Touryan J, Mullen T, Kothe C, Bigdely-Shamlo N (2020) How
sensitive are EEG results to preprocessing methods: a benchmarking study.
*IEEE Transactions on Neural Systems and Rehabilitation Engineering*
28:1081-1090.

Shoeb AH (2009) Application of machine learning to epileptic seizure onset
detection and treatment. PhD thesis, Massachusetts Institute of Technology.

Trübutschek D, Yang YF, Gianelli C, et al. (2024) EEGManyPipes: a
large-scale, grassroots multi-analyst study of electroencephalography
analysis practices in the wild. *Journal of Cognitive Neuroscience* 36(2).

Vinck M, Oostenveld R, van Wingerden M, Battaglia F, Pennartz CMA (2011) An
improved index of phase-synchronization for electrophysiological data in
the presence of volume-conduction, noise and sample-size bias.
*NeuroImage* 55:1548-1565.

Widmann A, Schröger E, Maess B (2015) Digital filter design for
electrophysiological data: a practical approach. *Journal of Neuroscience
Methods* 250:34-46.

Ziyabari S, Shah V, Golmohammadi M, Obeid I, Picone J (2017) Objective
evaluation metrics for automatic classification of EEG events.
arXiv:1712.10107.
