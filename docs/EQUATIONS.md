# Equations and method decisions

Every method in the pipeline with its mathematics, the decision it settles,
the rejected alternative, and links to code, requirement and evidence.
Numbers quoted as "measured" come from `results/validation/` and are
reproduced in [VALIDATION_REPORT.md](VALIDATION_REPORT.md).

## 1. Sampling and units

All data are float64 microvolts. EDF stores digital values $d$ with a
linear map to physical units,

$$x = p_{\min} + \frac{(d - d_{\min})(p_{\max} - p_{\min})}{d_{\max} - d_{\min}},$$

then MNE scales by the declared unit; the reader asks MNE for µV
explicitly (`get_data(units="uV")`). **Decides:** no stage ever multiplies
by $10^6$ itself. Test: `tests/test_io.py::test_units_are_microvolts`
(a file declared in mV comes out ×1000). Requirement F-01.

The pipeline never resamples. Its band-pass top (45 Hz) and detection band
(1-20 Hz) are below Nyquist for every sampling rate ≥ 128 Hz; the filter
stage refuses a low-pass at or above Nyquist.

## 2. Filters (F-06, V-05, ADR-004)

**Design.** Windowed-sinc FIR with a Hamming window. The main-lobe width of
the Hamming window gives the length needed for a transition band $\Delta f$:

$$N \approx \frac{3.3\, f_s}{\Delta f}\quad(\text{rounded up to odd}),$$

with about 53 dB stopband attenuation and 0.02 dB passband ripple.
Transition widths follow Widmann et al. (2015), as MNE does:

$$\Delta f_{\text{hp}} = \min(\max(0.25 f_{\text{hp}}, 2), f_{\text{hp}}),\qquad
\Delta f_{\text{lp}} = \min(\max(0.25 f_{\text{lp}}, 2), f_s/2 - f_{\text{lp}}).$$

For 0.5-45 Hz at 256 Hz: $\Delta f_{\text{hp}} = 0.5$ Hz, so
$N = 1691$ taps (6.6 s), and $\Delta f_{\text{lp}} = 11.25$ Hz.

**Zero phase without squaring.** A symmetric FIR of odd length has
constant group delay $\tau_g = (N-1)/(2 f_s)$. Convolving once and
discarding $(N-1)/2$ samples at the start (`mode="same"`) removes the delay
exactly: the output has zero phase and magnitude $|H(f)|$. Forward-backward
filtering (`filtfilt`) would also give zero phase but with magnitude
$|H(f)|^2$, doubling the attenuation in dB and widening the transition
band. Edges are padded by odd reflection, $x_{-k} = 2x_0 - x_k$.

**Rejected:** causal FIR (shifts every event by $\tau_g$ = 3.3 s at
0.5 Hz high-pass; negative-control test
`test_negative_control_causal_filter_delays_by_half_its_length`); IIR
Butterworth (non-linear phase unless applied twice, then $|H|^2$).

**Line noise.** Kenya's mains is 50 Hz. A band-stop FIR with −6 dB at
$50 \pm 1$ Hz and transition 1 Hz (845 taps at 256 Hz) gives ≥ 40 dB
attenuation over 49.6-50.4 Hz and ≤ 0.1 dB change at 45 Hz and below
(`test_notch_removes_mains_and_spares_neighbours`). Harmonics below Nyquist
are notched as well. The notch is narrow in frequency, so it rings in time
for about $N/f_s$ = 3.3 s; since the 45 Hz low-pass sits below 50 Hz, the
ringing lies outside the analysed band. Residual line noise is measured,
not assumed (F-05):

$$\text{LNR} = \frac{\int_{49}^{51} P(f)\,df}{\int_{1}^{45} P(f)\,df}.$$

## 3. Re-referencing (F-07, ADR-005)

Common average over the set $G$ of good channels:

$$\tilde x_i(t) = x_i(t) - \frac{1}{|G|} \sum_{j \in G} x_j(t).$$

The data rank drops by one (`test_car_zeroes_the_mean_of_good_channels_and_lowers_rank`),
which matters for any later ICA. Bad channels are excluded so one
disconnected electrode does not leak into every channel. **Not applied to
bipolar montages** (all channel names of the form `A-B`, as in CHB-MIT):
averaging derivations has no physical meaning. **Side effect, measured:** a
large focal discharge is spread by CAR into every channel at
$1/|G|$ of its amplitude; it raised the line-length z-score on distant
channels in synthetic data (BUILD_JOURNAL ISSUE-003).

## 4. Spectra (F-08, F-10)

Welch's estimate averages $K$ modified periodograms of length $L$:

$$\hat P(f) = \frac{1}{K} \sum_{k=1}^{K} \frac{|\sum_n w_n x_{n + kD} e^{-i 2\pi f n / f_s}|^2}{f_s \sum_n w_n^2}.$$

Hann window, $L = 2$ s, 50 % overlap: resolution $f_s/L = 0.5$ Hz, enough
to separate an alpha peak (sd 0.8-1.8 Hz) from its neighbours; the variance
of each bin falls roughly as $1/K$ (about $1/(1.9 \cdot T/L)$ with 50 %
Hann overlap). A 3-minute recording gives $K = 179$.

**Rejected:** single periodogram (variance does not fall with length);
multitaper (better leakage control, but specparam and the validation
literature use Welch; reproducibility of the comparison wins).
Parseval check: $\int \hat P\,df = \operatorname{var}(x)$ within 3 %
(`test_parseval_total_power_equals_variance`).

**Event windows are excluded** (`welch(..., exclude=...)`): a 3 Hz
spike-wave discharge in the background spectrum bent the aperiodic fit to
a negative exponent on the involved channels (BUILD_JOURNAL ISSUE-004).

Band power is the trapezoid integral of $\hat P$ over the band (µV²).

## 5. Aperiodic and periodic components (F-09, V-01-V-03, ADR-006)

Model (specparam "fixed" mode, Donoghue et al. 2020):

$$\log_{10} P(f) = b - \chi \log_{10} f + \sum_{k} h_k \exp\!\left(-\frac{(f - c_k)^2}{2 s_k^2}\right).$$

$b$ offset, $\chi$ exponent, $h_k$ peak height in log10 units above the
aperiodic fit, $s_k$ peak sd (specparam reports bandwidth $2 s_k$).

Algorithm (`features/aperiodic.py`):

```
fit range 2-40 Hz; y = log10 P, u = log10 f
(b, chi) <- least squares line y ~ u
repeat 3 times: keep points with residual <= median residual; refit     # peaks sit above the line
flat <- y - (b - chi u)
repeat up to max_peaks:
    i <- argmax flat;  h <- flat[i]
    stop if h < max(2 * sd(flat), 0.1)
    s <- half-height width on the shorter side / 1.1774, clipped to [0.5, 4] Hz
    flat <- flat - h exp(-(f - f_i)^2 / 2 s^2)
    drop the peak if it lies within s of the fit-range edge
joint bounded least squares over (b, chi, c_k, h_k, s_k)
```

**Decides:** whether a band-power difference is an oscillation or a change
of exponent (H1). **Rejected:** depending on specparam at runtime (API in
release-candidate churn); IRASA (no peak parameters). Measured on 200
synthetic spectra: see V-01-V-03 in the validation report. Fits with
$R^2 < 0.8$ or $\chi \notin [0, 4]$ are reported as unreliable and left out
of the averages.

## 6. Phase coupling (F-11, V-07, ADR-007)

Per 2 s epoch $e$ and frequency bin $f$ in 8-12 Hz, Hann-tapered Fourier
coefficients $X_i(e,f)$ and cross-spectrum
$S_{ij}(e,f) = X_i(e,f)\,\overline{X_j(e,f)}$.

$$\text{PLV}_{ij} = \Big\langle \Big|\tfrac{1}{E}\textstyle\sum_e S/|S|\Big| \Big\rangle_f,\qquad
\text{wPLI}_{ij} = \Big\langle \frac{|\sum_e \operatorname{Im} S|}{\sum_e |\operatorname{Im} S|} \Big\rangle_f.$$

Debiased squared wPLI (Vinck et al. 2011, eq. 33):

$$\text{dwPLI}^2_{ij} = \Big\langle \frac{(\sum_e \operatorname{Im} S)^2 - \sum_e (\operatorname{Im} S)^2}{(\sum_e |\operatorname{Im} S|)^2 - \sum_e (\operatorname{Im} S)^2} \Big\rangle_f.$$

Volume conduction mixes sources with real, instantaneous weights:
$x = A s$. For two sensors the cross-spectrum of the shared part is
$a_i a_j |S_s|^2$, real, so $\operatorname{Im} S$ carries only noise and
true lagged interaction. PLV counts the real part; wPLI does not.

**Decides:** report dwPLI as the coupling measure; PLV is shown only as a
contrast. **Finding:** plain wPLI has an upward small-sample bias of about
0.18 at the 95th percentile with 60 epochs and no coupling at all, failing
the pre-registered threshold at 2 minutes; the debiased estimator is near
zero (FINDINGS F-1). Epochs inside detected events are excluded.

## 7. Seizure-like event detection (F-12, V-06, V-10, ADR-008)

1. Band-limit to 1-20 Hz (zero-phase FIR, §2). Ictal rhythms are delta to
   alpha; muscle activity is mostly above 20 Hz.
2. Line length per channel in 2 s windows, 1 s step (Esteller et al. 2001):
   $$\text{LL}_w = \frac{1}{N}\sum_{n \in w} |x_n - x_{n-1}|.$$
   LL grows with both amplitude and frequency, and is cheap.
3. Robust z-score against the recording's own baseline:
   $$z_w = \frac{\log \text{LL}_w - \operatorname{median}(\log \text{LL})}{1.4826\,\operatorname{MAD}(\log \text{LL})}.$$
   The log makes the multiplicative LL change additive; median and MAD
   are not inflated by the events themselves (the same reasoning as
   Quiroga's $\hat\sigma = \operatorname{median}|x| / 0.6745$).
4. Vote: a window is active when at least a fraction $\phi$ of good channels
   have $z > \theta$. Merge active runs separated by at most $g$ seconds;
   drop runs shorter than $T_{\min}$.
5. Rhythmicity gate on the **fundamental of the background-normalised
   spectrum**. With $\bar P_e(f)$ the channel-averaged Welch spectrum of the
   event and $\bar P_b(f)$ that of the whole recording on the same channels,
   $$R(f) = \bar P_e(f) / \bar P_b(f), \qquad
   f_0 = \min\{f_k : f_k \text{ is a local maximum of } R,\ R(f_k) \ge \tfrac12 \max R\}.$$
   Keep the event if $f_0$ lies in the gate band. Dividing by $\bar P_b$
   removes the 1/f background, which otherwise puts the raw maximum at
   1-2 Hz for any real EEG segment (ISSUE-008); taking the lowest strong peak
   rather than the largest stops a spike-wave train's harmonics, boosted by
   the division, from hiding its fundamental (ISSUE-010).

$\theta$, $\phi$, $T_{\min}$, $g$ and the gate band (2-13 Hz or 2-7.5 Hz)
were chosen on synthetic tuning seeds 0-59 by a rule fixed before each run:
maximise sensitivity subject to at most 2 false detections per hour (first
1/h; revised when that proved infeasible, ISSUE-010), ties to the more
conservative setting. Selected: $\theta = 2.5$, $\phi = 0.05$ (one channel),
$T_{\min} = 10$ s, $g = 1$ s, gate 2-7.5 Hz (delta-theta).

**Scoring:** any-overlap (OVLP; Ziyabari et al. 2017): a true event is
detected if any detection overlaps it; a detection overlapping no true event
is a false detection. Sensitivity with a Wilson interval; false detections
per hour with an approximate Poisson 95 % upper bound
(Wilson-Hilferty).

**Rejected:** band-power ratio detectors (move with the aperiodic exponent,
H1); supervised classifiers on CHB-MIT (would need patient-grouped
cross-validation and more subjects; the evaluation here would be leaky).

## 8. Claim checking (F-16, V-08, ADR-009)

Contract: every number is written immediately before a citation
`[[dotted.key]]`. For a written number $w$ with $d$ decimals and the metric
value $v$:

$$\text{match} \iff |w - v| \le \tfrac{1}{2} 10^{-d}\;(+10^{-9}|v|).$$

Tokens: a *number* is a digit run not glued to a preceding letter, so
`T7`, `FT10` and `log10` are not numbers but `8-12`, `30s` and `10Hz`
expose every number. An *electrode token* is `[A-Z][A-Za-z]{0,3}\d{1,2}`
or `[A-Z][A-Za-z]{0,2}[zZ]`, optionally `A-B`, and must be in the
recording's channel list (`Hz` excepted). Diagnostic vocabulary
(epilepsy, seizure but not "seizure-like", diagnosis, abnormal, normal
EEG, pathology, ictal, disorder, disease, ...) is rejected, and the phrase
"research use only" is required.

**Validated by mutation testing** (H4): equivalent mutants are decided from
the metric values by an independent rounding rule, never by the checker
itself (a circular definition would hide every escape; BUILD_JOURNAL
ISSUE-006). Known blind spot: numbers written as words.

## 9. Statistics used in the validation report

Wilson score interval for a proportion $\hat p = k/n$:

$$\frac{\hat p + \frac{z^2}{2n} \pm z\sqrt{\frac{\hat p(1-\hat p)}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}},\quad z = 1.96.$$

Rule of three: zero failures in $n$ trials gives a 95 % upper bound of
about $3/n$ on the failure rate.

Poisson rate upper bound (Wilson-Hilferty) for $k$ events in exposure $T$:

$$\lambda_{95} \approx \frac{(k+1)\left(1 - \frac{1}{9(k+1)} + \frac{1.96}{3\sqrt{k+1}}\right)^3}{T}.$$

Benjamini-Hochberg is implemented (`core/stats.py`) for future per-channel
tests; no per-channel inference is reported in v0.1.

## 10. Ground-truth generators (`synth/eeg.py`)

**Spectral synthesis.** For $n$ samples at $f_s$, draw complex Gaussian
Fourier coefficients with amplitude
$A_k = \sqrt{P(f_k)\, f_s\, n / 2}$ so the expected one-sided PSD of
$x = \mathrm{irfft}(A_k Z_k)$ is exactly $P(f)$, the model of §5. Verified:
median log error < 0.03 (`test_shaped_noise_has_the_specified_spectrum`).

**Spike-wave discharges.** Instantaneous rate gliding from $f_0 \in [3,5]$
to $f_1 \in [2, f_0]$ Hz, phase $\phi(t) = 2\pi \int f\,dt$; waveform
$-\exp(-\delta(\phi)^2 / 2\sigma_s^2) + 0.6\exp(-\delta(\phi - 0.7\pi)^2/2\sigma_w^2)$
with spike width 25 ms and wave width 120 ms, unit RMS, 2 s cosine ramps.
Amplitude on channel $i$: $10^{\text{SNR}/20}\cdot \text{RMS}_i^{\text{background}} \cdot g_i$
with $g_i = \exp(-(d_i/r)^2)$ for scalp distance $d_i$ from a random centre.

**Volume conduction.** Six independent alpha sources at random scalp
positions; sensor gains $1/(0.3 + d)^2$; no source is coupled to another.
**Coupled pair:** the second source is the first delayed by 25 ms (a
quarter cycle at 10 Hz), with 30 % cross-mixing and 30 % noise.

**Artifacts.** Blinks: Gaussian bumps of 80-200 µV, sd 80 ms, frontal
gains 1.0 (Fp1, Fp2) and 0.4 (F-row). Muscle: 20-60 Hz band-limited noise,
1-6 s, 1-3 of six temporal/frontal sites, 1-3 times background RMS. Line
noise: 50 Hz sinusoid. Flat channel: a constant offset; noisy channel:
added white noise at 15 times the median robust SD.
