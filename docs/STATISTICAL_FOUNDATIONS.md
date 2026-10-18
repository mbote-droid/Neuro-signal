# Statistical foundations

The probability models behind the design decisions, each tested the same
way: **state what the model predicts, then measure it.** Predictions come
from the model alone; measurements come from the pipeline. Every number
links to a result file written by `validation/theory.py` (`make theory`),
with provenance and a SHA-256 entry in the manifest.

Where a model fails, that is reported too: two of the eight checks below
did not match on the first attempt, and what we learned from the mismatch
is part of the record.

| # | decision it justifies | model | predicted | measured | verdict |
|---|---|---|---|---|---|
| 1 | read H1's failure correctly | Welch sampling distribution | per-bin noise 0.0334 log10 | 0.033 | match |
| 1b | | linearised least squares | height-difference SD 0.038 | 0.057 | estimator 1.5x above the floor |
| 2 | report debiased wPLI | Laplace null of Im S | wPLI 0.1457 (60 epochs) | 0.1455 | match |
| 3 | fit in log space | Whittle maximum likelihood | efficiency ratio ≈ 1 | 0.995 | match |
| 4 | rhythm-gate floor; blink failure | Fourier transform of a blink train | ratio peak 1.63 Hz | 1.5 Hz | match |
| 5 | tune the merge gap | Poisson point process | 13.7 and 0.07 long runs/h (5 s, 1 s gap) | 21.9 and 0.3 | same order; model low |
| 6 | median/MAD z-scores | contamination (mixture) model | classical z collapses first | yes, at every level | match |
| 7 | how to read H6 | binomial power | 7 seizures cannot decide 57 % vs 60 % | Wilson width 0.59 | design lesson |
| 8 | choose thresholds | Neyman-Pearson | constrained operating point | the tuning rule | by construction |

## 1. Why H1 failed: sampling noise, then estimator inefficiency

**Model.** A Welch estimate averages $K$ Hann-windowed periodograms with
50 % overlap. Each bin is approximately $P(f)\,\chi^2_\nu/\nu$ with
equivalent degrees of freedom (Welch 1967)

$$\nu = \frac{2K}{1 + 2\rho^2}, \qquad \rho = \tfrac16 \text{ for Hann at 50 \% overlap.}$$

For 180 s and 2 s windows, $K = 179$ and $\nu = 339$. The noise of
$\log_{10}$ of a $\chi^2_\nu/\nu$ variable has SD $\sqrt{\psi'(\nu/2)}/\ln 10$,
where $\psi'$ is the trigamma function, so

$$\sigma_{\text{bin}} = 0.0334 \;\log_{10} \text{ units}.$$

Hann's three-term spectral kernel ($\tfrac12, -\tfrac14, -\tfrac14$) makes
adjacent bins correlated, with coefficient $(2/3)^2 = 0.444$ at lag 1 and
$(1/6)^2 = 0.028$ at lag 2. Propagating this through the linearised
least-squares fit (sandwich covariance
$(J^\top J)^{-1} J^\top \Sigma J (J^\top J)^{-1}$, with $J$ the Jacobian of the
spectral model at the true parameters) gives the standard error of the
fitted alpha height. Two independent recordings differ by $\sqrt 2$ times
that.

**Prediction vs measurement**
([`theory_h1_noise.json`](../results/validation/theory_h1_noise.json)):

* per-bin noise: predicted 0.0334, measured 0.033 by Monte Carlo. The
  sampling model is right;
* SD of the height difference over H1's 200 cases: predicted 0.038, measured
  0.057 (robust SD). The fraction within the pre-registered 0.05 was
  predicted at 81 % and measured at 60.5 %.

The linear theory explains about half of the variance. The first
hypothesis for the rest, that the fitter finds different numbers of peaks
in the two recordings, was **tested and rejected**: fits with equal peak
counts were noisier (0.065), not quieter. A direct Monte Carlo on fixed
spectra located the gap instead: the peak-height estimator varies
1.3-1.8 times more than the linear floor, and underestimates height by
0.02-0.04 log10, consistent with the Hann window smearing narrow peaks.
Check 3 shows that switching to maximum likelihood does not remove this.

**What this decides.** H1's rejection is two effects, now separated: an
unavoidable sampling floor (about 0.038 for a 3-minute recording; 90 %
within 0.05 would need about 280 s even for an ideal estimator) and an
estimator inefficiency of about 1.5x. The fix for the second is to model
the window: fit the spectrum convolved with Hann's kernel, or use multitaper
spectra with a known kernel. That is future work with a measurable target.

## 2. Why the coupling measure is debiased wPLI

**Model.** With no coupling, the imaginary part of the cross-spectrum of two
independent complex Gaussian signals, $X = \operatorname{Im}(z_1\bar z_2)$,
has a Laplace distribution: the difference of two products of independent
normals. For Laplace, $\operatorname{SD}/E|X| = \sqrt 2$. Over $N$ epochs
$|\sum X| \approx \operatorname{SD}\sqrt{2N/\pi}$ and $\sum|X| \approx N\,E|X|$, so

$$E[\text{wPLI} \mid \text{no coupling}] \approx \frac{2}{\sqrt{\pi N}}.$$

The debiased estimator's numerator,
$\sum_{e \ne e'} X_e X_{e'} = (\sum X)^2 - \sum X^2$, is a U-statistic: its
expectation is exactly zero under the null.

**Prediction vs measurement**
([`theory_wpli_bias.json`](../results/validation/theory_wpli_bias.json),
20 seeds of 19 independent channels, and the same for the volume-conduction
mixture):

| epochs | predicted wPLI | measured, independent | measured, mixed | debiased, measured |
|---|---|---|---|---|
| 60 (2 min) | 0.1457 | 0.1455 | 0.1453 | 0.0003 |
| 300 (10 min) | 0.0651 | 0.0655 | 0.0665 | 0.0001 |

**What this decides.** FINDINGS F-1 (wPLI of 0.19 at the 95th percentile
with no coupling) is not a quirk; it is the predicted $1/\sqrt N$ bias.
Debiased wPLI removes it by construction, so it is the reported measure, and
H3's pre-registered bound was violated by an estimator property that could
have been computed in advance. Lesson for the next pre-registration:
derive the null distribution of the statistic before setting a threshold.

## 3. Why fitting in log space is (near-)optimal: maximum likelihood

**Model.** The exact likelihood of a Welch spectrum under the model $P(f;\theta)$
is the Whittle (Gamma) likelihood

$$-\log L(\theta) = \frac{\nu}{2} \sum_f \left[\log P(f;\theta) + \frac{\hat P(f)}{P(f;\theta)}\right] + \text{const}.$$

The pipeline instead minimises $\sum_f(\log \hat P - \log P)^2$. Because
$\log \hat P = \log P + \varepsilon$ with near-Gaussian $\varepsilon$ of
constant variance for large $\nu$, least squares in log space is
asymptotically as efficient as the MLE, with one predictable difference: a
constant offset bias $(\psi(\nu/2) - \ln(\nu/2))/\ln 10 \approx -1/(\nu \ln 10)$.

**Prediction vs measurement**
([`theory_whittle.json`](../results/validation/theory_whittle.json),
200 spectra):

* exponent RMSE: least squares 0.0209, Whittle MLE 0.0208; relative efficiency 0.995;
* offset bias: predicted −0.0013, measured −0.0008 (least squares minus MLE);
* alpha-height RMSE: 0.0511 vs 0.0514. Maximum likelihood does not fix the
  estimator gap of check 1, which confirms that the gap comes from the model
  (window smearing), not the loss function.

**What this decides.** Log-space least squares is the maximum-likelihood
fit in disguise for spectra this long; keeping it costs nothing measurable
and avoids an iterative optimiser in the report path.

## 4. Why blinks look like a 2 Hz rhythm

**Model.** The generator's blink is a Gaussian bump with SD
$\sigma = 80$ ms. A Poisson train of such bumps has PSD
$\lambda|G(f)|^2 \propto e^{-4\pi^2\sigma^2 f^2}$. The rhythm gate divides by the
background, $\propto f^{-\chi}$, so the blink ratio spectrum is
$f^{\chi} e^{-4\pi^2\sigma^2 f^2}$, which peaks at

$$f^* = \sqrt{\frac{\chi}{8\pi^2\sigma^2}} \approx 1.6\text{-}2.1 \text{ Hz for } \chi = 1\text{-}2.2.$$

**Prediction vs measurement**
([`theory_blinks.json`](../results/validation/theory_blinks.json), 20
blink-only recordings): predicted median 1.63 Hz; measured fundamental of
73 blink events 1.5 Hz (interquartile range 1.0-2.0 Hz).

**What this decides.** The blink "rhythm" sits just below the gate's 2 Hz
floor, by physics, not by chance. That is why the floor exists and why it is
fragile: the three held-out chb03 seizures that were missed had fundamentals
of 1.0-1.5 Hz, the same band as blinks (FINDINGS F-7). The spectrum alone
cannot separate them; the next discriminator has to be spatial (blinks are
frontal and symmetric).

## 5. Why the merge gap matters: blinks as a Poisson process

**Model.** Supra-threshold blinks arrive as a Poisson process with rate
$\lambda$; each makes an active span of length $a$; spans closer than the
merge gap $g$ join. The rate of merged runs at least $T_{\min} = 10$ s long
then depends steeply on $g$, because a run needs several blinks in a row each
within $a + g$ of the last, a probability that falls geometrically.

**Calibration.** $a = 2.0$ s, the median isolated-blink span. The rate is
the one the detector actually sees: 4.6 supra-threshold blinks per minute,
not the generator's nominal 15 (smaller blinks never cross the threshold).
The first version used the nominal rate and over-predicted by 3.5-30x; the
mismatch is kept in the result file.

**Prediction vs measurement** (long runs per hour before the rhythm gate):

| merge gap | predicted | measured |
|---|---|---|
| 5 s | 13.7 | 21.9 |
| 1 s | 0.07 | 0.3 |

Same order of magnitude and the same conclusion: the gap alone moves blink
false events from tens per hour to under one. The model runs low, as
expected from its fixed span (real spans vary, and variable spans merge
more easily).

**What this decides.** ISSUE-011 (blink trains merged into "rhythms") was a
predictable consequence of Poisson clustering with a 5 s gap; the tuned 1 s
gap is the setting the model says suppresses it.

## 6. Why the z-score is robust: contamination

**Model.** Background windows $\sim N(0,1)$ in log line length; event
windows $\sim N(\Delta, 1)$; a fraction $\varepsilon$ of windows are events.
With the mean and SD, an event's z-score is

$$z_{\text{classical}} = \frac{\Delta(1-\varepsilon)}{\sqrt{1 + \varepsilon(1-\varepsilon)\Delta^2}},$$

which collapses quickly because the events inflate the SD. The median and
MAD have a 50 % breakdown point; their z-score (computed numerically from
the mixture's quantiles) degrades slowly.

**Prediction vs measurement**
([`theory_robust_z.json`](../results/validation/theory_robust_z.json)):
for $\Delta = 6$ the classical z falls below the detector's threshold (2.5)
at $\varepsilon \approx 0.1$; the robust z stays above it until
$\varepsilon \approx 0.3$. In synthetic recordings with 1-4 one-minute
discharges (measured $\varepsilon$ = 0.08-0.33), the robust z exceeded the
classical z at every level (2.76 vs 2.14 at 8 % contamination; 2.54 vs
1.52 at 16 %), and only the robust z stayed above threshold up to 16 %.

**What this decides.** A recording with a long seizure is exactly the case
that matters; a classical z-score would hide the seizure in its own
baseline. The measured event z-scores are lower than the $\Delta = 6$
curve (6 dB discharges are weaker), which is also why low-SNR, long
events are the detector's weakest case.

## 7. Why H6 could not settle its question: power

**Model.** The number of detected seizures is $\text{Binomial}(n, p)$.

**Computation** ([`theory_power.json`](../results/validation/theory_power.json)):

* with $n = 7$, the pre-registered rule "at least 60 %" passes with
  probability 0.42 when the true sensitivity is 0.60, and fails 15 % of the
  time even when it is 0.80. H6 was close to a coin flip by design;
* the observed 4/7 has a Wilson 95 % interval of [0.25, 0.84], 0.59 wide;
* to show a lower bound above 0.6 with 80 % power: about 76 seizures if the
  true sensitivity is 0.75, 41 if 0.80, 177 if 0.70;
* to bound false detections below 2/h with 80 % power: about 12 h of
  recording if the true rate is 1/h, 4.4 h if 0.5/h.

**What this decides.** The next confirmatory test must be sized, not
chosen by convenience: several CHB-MIT subjects, held out together. This is
also the quantitative case for the data and compute in a funding proposal.

## 8. Why the tuning rule has that form: Neyman-Pearson

Choosing detector thresholds to maximise sensitivity subject to a ceiling
on false detections per hour is the Neyman-Pearson formulation of
detection: fix the false-alarm rate, then maximise power. The tuning grid
traces the operating characteristic, and the rule picks the most sensitive
point under the ceiling (`validation/tune_detector.py`). The ceiling itself
came from the application (alarm fatigue, Ziyabari et al. 2017), and when
it proved infeasible on realistic data it was relaxed to H2's own
pre-registered limit, a decision recorded in BUILD_JOURNAL ISSUE-010.

## What is not claimed

* **No EM, HMM or Bayesian model is used in v0.1.** The merge gap and
  minimum duration are crude, hand-tuned duration priors. A hidden
  semi-Markov model fitted by expectation-maximisation would learn state
  durations from data; it is the natural next model, not a retrofit.
* The models above are approximations: large-$\nu$ log-normality,
  white-noise bin correlations, a fixed blink span, a Gaussian mixture for
  log line length. Where they miss (checks 1b and 5), the size of the miss
  is reported.

## References

Gelman A, Loken E (2014) The statistical crisis in science. *Am Sci* 102:460.
· Hampel FR (1974) The influence curve and its role in robust estimation.
*J Am Stat Assoc* 69:383. · Neyman J, Pearson ES (1933) *Phil Trans R Soc A*
231:289. · Percival DB, Walden AT (1993) *Spectral Analysis for Physical
Applications*. Cambridge. · Vinck M et al. (2011) *NeuroImage* 55:1548. ·
Welch PD (1967) *IEEE Trans Audio Electroacoust* 15:70. · Whittle P (1953)
*Ark Mat* 2:423. · Ziyabari S et al. (2017) arXiv:1712.10107.
