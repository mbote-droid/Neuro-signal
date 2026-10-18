# Data

## 1. Real data

| dataset | use | licence and access | version and integrity |
|---|---|---|---|
| CHB-MIT Scalp EEG Database (Shoeb 2009; Goldberger et al. 2000, PhysioNet) | H5 (subject chb01: 10 files, 9.6 h, 7 seizures; a development set after the first run), H6 (subject chb03: 10 files, 10.0 h, 7 seizures; held out, one run) | Open Data Commons Attribution License v1.0; open access, no credentialing | v1.0.0; every file checked against PhysioNet's `SHA256SUMS.txt`; hashes are also stored in `results/validation/chbmit*.json` |

Download: `make data` (runs `scripts/fetch_chbmit.py`), from PhysioNet's
open-data mirror on AWS (`physionet-open` bucket). Files go to `data/raw/`,
which is git-ignored and treated as read-only.

**CHB-MIT specifics that shaped the design:** 256 Hz, bipolar
double-banana montage (so no common average reference, ADR-005), one
derivation (`T8-P8`) recorded twice with identical samples (collapsed by the
reader), paediatric subjects with intractable seizures, expert onset and
offset times in `chbNN-summary.txt` (parsed by
`validation/campaign.py::parse_summary`).

**Citation (required by the licence):** Shoeb AH. *Application of Machine
Learning to Epileptic Seizure Onset Detection and Treatment.* PhD thesis,
MIT, 2009. Goldberger AL, et al. PhysioBank, PhysioToolkit, and PhysioNet.
*Circulation* 101(23):e215-e220, 2000.

## 2. Ethics and law

* Only public, de-identified data were used; no new data were collected, so
  no ethics committee approval was needed for this work. Collecting new
  recordings would need it first.
* The reader drops every EDF header field except signal, rate, channel
  names and annotations; patient name, birth date, sex, hand, recording
  description and measurement date never enter a `Recording` (S-02,
  `tests/test_io.py`). EDF+ annotation text is kept (truncated to 200
  characters) and could in principle contain identifiers: review it before
  sharing a report from a clinical source.
* The subject id in reports is `rec-` plus the first 12 hex digits of the
  file's SHA-256: pseudonymous, not anonymous (anyone holding the file can
  recompute it).
* The Kenya Data Protection Act 2019 treats health data as sensitive
  personal data; GDPR and HIPAA apply where the data's origin requires.
  Processing is local and ephemeral: nothing is uploaded unless the user
  chooses the LLM explainer, and then only the metrics dictionary (S-03).

## 3. Synthetic data

All generators are in `src/neurosignal/synth/eeg.py`; equations in
[EQUATIONS.md](EQUATIONS.md) §10. Seeds expand through
`numpy.random.SeedSequence([seed, stream...])`, one stream per component, so
adding an artifact type never changes the background of an existing seed.

| generator | parameters (distributions) | used by |
|---|---|---|
| `random_spectrum` | offset U(1, 2); exponent U(0.8, 2.2); alpha peak at U(8, 12) Hz, height U(0.3, 1.0) log10, sd U(0.8, 1.8) Hz; beta peak with probability 0.5 at U(17, 28) Hz | V-01-V-03, H1 |
| `make_recording` | 19 channels of the 10-20 system; per-channel jitter of offset (sd 0.1), exponent (sd 0.1), peak frequency (sd 0.3 Hz) and height (sd 0.1) | QC, detection, checker, examples |
| spike-wave discharges | two per recording (none in one recording of five); duration U(15, 60) s, ≥ 30 s apart; rate from U(3, 5) Hz gliding to U(2, f0) Hz; regional spread with radius U(0.6, 1.2) on the unit scalp disc; SNR 0, 3, 6 or 10 dB relative to each channel's background RMS | H2, tuning |
| blinks | Poisson rate per minute; 80-200 µV, sd 80 ms; Fp1/Fp2 gain 1, F-row 0.4 | H2, QC |
| muscle | Poisson rate per minute; 1-6 s of 20-60 Hz noise on 1-3 of T7, T8, F7, F8, P7, P8 at 1-3 times background RMS | H2, tuning |
| alpha and spindle bursts | Poisson rate per minute; 70 %: 3-30 s at U(8, 13) Hz on P3, Pz, P4, P7, P8, O1, O2; 30 %: 0.8-2.5 s at U(11, 15) Hz on F3, Fz, F4, C3, Cz, C4; 1.5-4 times background RMS | H2, tuning |
| line noise | 50 Hz, amplitude U(0, 20) µV in detection sets | QC, H2 |
| bad channels | flat: constant offset U(-5, 5) µV; noisy: added white noise at 15 times the median robust SD | V-04 |
| `mixed_sources` | 6 independent 10 Hz alpha sources, random positions, gains 1/(0.3 + d)², 5 % sensor noise | H3 |
| `coupled_pair` | one source and its 25 ms delayed copy, 30 % cross-mixing, 30 % noise | H3 |

Seed sets: tuning 0-59 (detector thresholds only); detection evaluation
1000-1199; QC 2000-2099; checker 3000-3059; aperiodic 0-199 (stream 77);
H1 0-199 (streams 101/102).

## 4. Memory plan (8 GB target)

A recording is loaded once as float64 (8 bytes per sample). Filtering and
spectra run one channel at a time; coupling caps the analysed span at
600 s of epochs. Measured peak resident memory for 1 hour of 32 channels at
256 Hz (236 MB of signal) is in the validation report (P-01). Files above
2 GB are refused before parsing; chunked overlap-save processing would be
needed beyond that (ADR-012).
