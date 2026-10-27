# H7c audit: reading guide

The same items as audit_items.md, in the same order. Under each sentence that cites a number: the cited value and what that metric measures. The notes are identical for every item and say nothing about whether a sentence is right; the verdicts (0 or 1 in audit.csv) are yours.

## A01

> ### Summary

> This report summarizes an electrophysiological analysis intended for research use only.

> The pipeline evaluated 19 [[recording.n_channels]] channels over a session lasting 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> Spectral modeling was achieved across 17 [[aperiodic.n_channels_with_alpha]] clean channels, and the detector isolated 1 [[events.n_events]] seizure-like event.
- `aperiodic.n_channels_with_alpha` = 17: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> Data were collected using a referential montage across 19 [[recording.n_channels]] scalp electrodes at a sampling rate of 256.0 [[recording.sfreq_hz]] Hz, covering a total duration of 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 120.0: length of the recording in seconds.

> ### Quality

> Channel quality screening retained 17 [[qc.n_good]] channels and flagged 2 [[qc.n_bad]] channels.
- `qc.n_good` = 17: channels kept after quality control.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Specifically, Cz showed flat recording behavior lasting 119.996 [[qc.flat.Cz]] seconds, while channel T8 demonstrated high variance with a noisy ratio of 30.616 [[qc.noisy.T8]].
- `qc.flat.Cz` = 119.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.noisy.T8` = 30.616: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.

> Median line noise ratio dropped from 0.3448 [[qc.line_noise_ratio_before_median]] before filtering down to 0.0000218 [[qc.line_noise_ratio_after_median]] post-processing.
- `qc.line_noise_ratio_before_median` = 0.344766: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 2.17709e-05: the same ratio AFTER the 50 Hz notch filter.

> ### Spectrum

> Standard band power mixes oscillations with the aperiodic background (peak power above the aperiodic fit is the oscillation measure).

> Across 87 [[spectral.n_segments]] clean segments, the mean alpha band power was 13.08 [[spectral.alpha_band_power_uv2.mean]] µV², with mean relative alpha power reaching 0.12 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 87: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 13.0848: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.120747: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Aperiodic parameterization showed an average exponent of 1.76 [[aperiodic.exponent.mean]], an offset of 1.75 [[aperiodic.offset.mean]], and an average fit R² of 0.995 [[aperiodic.r_squared.mean]] with 0 [[aperiodic.n_poor_fits]] poor fits.
- `aperiodic.exponent.mean` = 1.75952: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.74709: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.r_squared.mean` = 0.995462: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.

> Alpha oscillatory peaks emerged in 17 [[aperiodic.n_channels_with_alpha]] channels, showing a mean peak frequency of 11.27 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and an average peak power above the aperiodic fit of 0.79 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 17: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 11.2736: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.785619: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ### Coupling

> Inter-channel connectivity was assessed across 44 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 44: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> Metric estimates should note that PLV is inflated by volume conduction while debiased wPLI is not.

> The mean phase locking value was 0.14 [[connectivity.plv_mean]], compared to a mean debiased wPLI of 0.00089 [[connectivity.dwpli_mean]] and mean wPLI of 0.17 [[connectivity.wpli_mean]].
- `connectivity.plv_mean` = 0.1402: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000888884: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.
- `connectivity.wpli_mean` = 0.16947: plain wPLI averaged over pairs. Ignores zero-lag sync but is biased UPWARD with few epochs (about 0.15 even with no coupling at 60 epochs).

> The pair with highest debiased wPLI was Pz–P4 at 0.097 [[connectivity.top_pairs.0.dwpli]] (PLV of 0.18 [[connectivity.top_pairs.0.plv]]), followed by Fp2–Pz at 0.068 [[connectivity.top_pairs.1.dwpli]].
- `connectivity.top_pairs.0.dwpli` = 0.0968219: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.178415: PLV of this pair (inflated by volume conduction).
- `connectivity.top_pairs.1.dwpli` = 0.0679899: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.

> ### Events

> Event detection marked 1 [[events.n_events]] seizure-like event, reflecting a rate of 30.0 [[events.rate_per_hour]] per hour and 31.0 [[events.total_duration_s]] seconds of total event duration.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 30.0: candidates per hour of recording.
- `events.total_duration_s` = 31.0: total seconds covered by candidates.

> Spanning from onset at 70.0 [[events.list.0.onset_s]] seconds to offset at 101.0 [[events.list.0.offset_s]] seconds (duration of 31.0 [[events.list.0.duration_s]] seconds), this event engaged 17 [[events.list.0.n_channels]] channels with a dominant frequency of 4.0 [[events.list.0.dominant_freq_hz]] Hz and peak line-length z-score of 7.78 [[events.list.0.peak_z]].
- `events.list.0.onset_s` = 70.0: when this candidate starts (seconds from the start).
- `events.list.0.offset_s` = 101.0: when this candidate ends (seconds).
- `events.list.0.duration_s` = 31.0: how long this candidate lasts (seconds).
- `events.list.0.n_channels` = 17: channels where the candidate was seen.
- `events.list.0.dominant_freq_hz` = 4.0: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.0.peak_z` = 7.77655: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

## A02

> ## Summary

> This automated EEG analysis report is provided for research use only.

> The dataset consists of a referential recording across 19 [[recording.n_channels]] channels with a duration of 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> The processing pipeline evaluated data quality, parameterized spectral properties into periodic oscillations and aperiodic background components, measured sensor-level functional connectivity, and screened for discrete events.

> ## Recording

> The data file contains 19 [[recording.n_channels]] channels recorded in a referential montage at a sampling rate of 256.0 [[recording.sfreq_hz]] Hz for a total duration of 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 300.0: length of the recording in seconds.

> ## Quality

> Data quality evaluation identified 2 [[qc.n_bad]] bad channels and 17 [[qc.n_good]] good channels.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 17: channels kept after quality control.

> Channel F7 remained flat for 299.996 [[qc.flat.F7]] seconds, and channel F4 was flagged as noisy with a metric of 32.531 [[qc.noisy.F4]].
- `qc.flat.F7` = 299.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.noisy.F4` = 32.531: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.

> Following notch filtering, the median line noise ratio decreased from 0.296189 [[qc.line_noise_ratio_before_median]] to 0.000202774 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.296189: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000202774: the same ratio AFTER the 50 Hz notch filter.

> ## Spectrum

> Across 299 [[spectral.n_segments]] segments, mean alpha band power was 12.8228 [[spectral.alpha_band_power_uv2.mean]].
- `spectral.n_segments` = 299: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 12.8228: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)

> Standard band power mixes oscillations with the aperiodic background (peak power above the aperiodic fit is the oscillation measure).

> Oscillatory alpha peaks were identified in 16 [[aperiodic.n_channels_with_alpha]] channels, yielding a mean alpha peak frequency of 9.54575 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean peak power of 0.291391 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 16: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 9.54575: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.291391: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> The aperiodic background model showed 0 [[aperiodic.n_poor_fits]] poor fits, with a mean exponent of 1.57225 [[aperiodic.exponent.mean]], a mean offset of 1.8568 [[aperiodic.offset.mean]], and a mean fit R-squared of 0.997602 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.exponent.mean` = 1.57225: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.8568: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.r_squared.mean` = 0.997602: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ## Coupling

> Connectivity estimated across 150 [[connectivity.n_epochs]] epochs showed a mean phase-locking value of 0.0872831 [[connectivity.plv_mean]] and a mean debiased weighted phase lag index of 0.000347631 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 150: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.0872831: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000347631: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> PLV is inflated by volume conduction while debiased wPLI is not.

> The pair with the highest debiased wPLI was F3 to Cz at 0.0446981 [[connectivity.top_pairs.0.dwpli]], which had an associated PLV of 0.120554 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0446981: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.120554: PLV of this pair (inflated by volume conduction).

> ## Events

> The detection module identified 0 [[events.n_events]] seizure-like events, corresponding to an event rate of 0.0 [[events.rate_per_hour]] per hour and a cumulative duration of 0.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A03

> ### Summary

> This analysis is for research use only.

> The dataset contains 19 [[recording.n_channels]] channels recorded for 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> The processing pipeline detected 1 [[events.n_events]] seizure-like event.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> Spectral parameterization identified clear alpha oscillations across 18 [[aperiodic.n_channels_with_alpha]] channels, while quality screening detected 1 [[qc.n_bad]] flat channel.
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> ### Recording

> Data were collected across 19 [[recording.n_channels]] channels in a referential montage at a sampling rate of 256.0 [[recording.sfreq_hz]] Hz, with a total duration of 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 300.0: length of the recording in seconds.

> ### Quality

> Data quality checks identified 18 [[qc.n_good]] good channels and 1 [[qc.n_bad]] bad channel.
- `qc.n_good` = 18: channels kept after quality control.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Channel F3 was flagged as flat for 299.996 [[qc.flat.F3]] seconds.
- `qc.flat.F3` = 299.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.

> Line noise artifact reduction reduced the median line noise ratio from 0.44 [[qc.line_noise_ratio_before_median]] before cleaning down to 0.00039 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.439635: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000386144: the same ratio AFTER the 50 Hz notch filter.

> ### Spectrum

> Standard band power mixes oscillations with the aperiodic background; peak power above the aperiodic fit is the oscillation measure.

> Across the montage, mean alpha band power was 16.57 [[spectral.alpha_band_power_uv2.mean]], and mean relative alpha power was 0.19 [[spectral.relative_alpha_power.mean]].
- `spectral.alpha_band_power_uv2.mean` = 16.5717: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.185582: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Aperiodic background decomposition showed a mean exponent of 1.17 [[aperiodic.exponent.mean]] and a mean offset of 1.24 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.17453: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.24097: overall height (log10 power) of the 1/f background. (average over channels)

> Across the 18 [[aperiodic.n_channels_with_alpha]] channels showing oscillatory peaks, the mean alpha peak frequency was 8.37 [[aperiodic.alpha_peak_freq_hz.mean]] Hz, with a mean alpha peak power above the aperiodic fit of 0.81 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 8.37273: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.806881: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ### Coupling

> Phase synchrony was calculated across 141 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 141: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> PLV is inflated by volume conduction while debiased wPLI is not.

> The mean PLV was 0.084 [[connectivity.plv_mean]], and the mean debiased wPLI was -0.00050 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.0844612: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = -0.000502753: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> The strongest coupling occurred between channels F7 and T7, showing a debiased wPLI of 0.043 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.13 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0431144: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.125627: PLV of this pair (inflated by volume conduction).

> ### Events

> The detection algorithm marked 1 [[events.n_events]] seizure-like event, reflecting a rate of 12.0 [[events.rate_per_hour]] events per hour.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 12.0: candidates per hour of recording.

> This event started at 64.0 [[events.list.0.onset_s]] seconds and ended at 82.0 [[events.list.0.offset_s]] seconds, spanning 18.0 [[events.list.0.duration_s]] seconds across 13 [[events.list.0.n_channels]] channels.
- `events.list.0.onset_s` = 64.0: when this candidate starts (seconds from the start).
- `events.list.0.offset_s` = 82.0: when this candidate ends (seconds).
- `events.list.0.duration_s` = 18.0: how long this candidate lasts (seconds).
- `events.list.0.n_channels` = 13: channels where the candidate was seen.

> It exhibited a dominant frequency of 3.5 [[events.list.0.dominant_freq_hz]] Hz and reached a peak amplitude statistic of 4.47 [[events.list.0.peak_z]].
- `events.list.0.dominant_freq_hz` = 3.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.0.peak_z` = 4.46796: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

## A04

> ### Summary

> This analysis is for research use only.

> The dataset includes 19 [[recording.n_channels]] channels recorded over 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> Pipeline processing detected 2 [[events.n_events]] seizure-like events covering a total duration of 116.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.total_duration_s` = 116.0: total seconds covered by candidates.

> Aperiodic spectral parameterization revealed a mean exponent of 2.02 [[aperiodic.exponent.mean]].
- `aperiodic.exponent.mean` = 2.02281: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)

> ### Recording

> The recording was performed using a referential montage comprising 19 [[recording.n_channels]] channels sampled at 256.0 [[recording.sfreq_hz]] Hz for 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 300.0: length of the recording in seconds.

> ### Quality

> Data quality checks identified 0 [[qc.n_bad]] bad channels and retained 19 [[qc.n_good]] clean channels.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 19: channels kept after quality control.

> The median line noise ratio was reduced from 0.0038 [[qc.line_noise_ratio_before_median]] to 0.00000054 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.00384112: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 5.3525e-07: the same ratio AFTER the 50 Hz notch filter.

> Parametric fitting of the power spectra was robust across channels, with 0 [[aperiodic.n_poor_fits]] poor fits and a mean r-squared value of 0.998 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.997756: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Excluding windows containing events, analysis across 181 [[spectral.n_segments]] segments showed a mean alpha band power of 2.49 [[spectral.alpha_band_power_uv2.mean]] microvolts squared and a mean relative alpha power of 0.044 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 181: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 2.49489: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0437229: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Standard band power mixes oscillations with the aperiodic background (peak power above the aperiodic fit is the oscillation measure).

> The underlying aperiodic model fit had a mean offset of 1.61 [[aperiodic.offset.mean]] and an exponent of 2.02 [[aperiodic.exponent.mean]].
- `aperiodic.offset.mean` = 1.60845: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.exponent.mean` = 2.02281: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)

> Oscillatory peaks in the alpha range were detected in 18 [[aperiodic.n_channels_with_alpha]] channels, yielding a mean peak frequency of 11.07 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and an average peak power above the aperiodic background of 0.30 [[aperiodic.alpha_peak_power.mean]], with highest peak power reaching 0.53 [[aperiodic.alpha_peak_power.max]] at channel P7.
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 11.067: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.299591: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)
- `aperiodic.alpha_peak_power.max` = 0.527744: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (highest channel)

> ### Coupling

> Phase coupling across 91 [[connectivity.n_epochs]] epochs resulted in a mean phase-locking value (PLV) of 0.10 [[connectivity.plv_mean]], an average weighted phase-lag index (wPLI) of 0.12 [[connectivity.wpli_mean]], and a debiased wPLI (dwPLI) of -0.0010 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 91: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.0998857: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.wpli_mean` = 0.116392: plain wPLI averaged over pairs. Ignores zero-lag sync but is biased UPWARD with few epochs (about 0.15 even with no coupling at 60 epochs).
- `connectivity.dwpli_mean` = -0.000976079: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> In functional connectivity, PLV is inflated by volume conduction while debiased wPLI is not.

> The channel pair with the strongest dwPLI synchronization was channel F7 and channel P3, with a dwPLI of 0.048 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.14 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.048394: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.142135: PLV of this pair (inflated by volume conduction).

> ### Events

> The detection routine captured 2 [[events.n_events]] seizure-like events, corresponding to an hourly rate of 24.0 [[events.rate_per_hour]].
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 24.0: candidates per hour of recording.

> The initial seizure-like event began at 21.0 [[events.list.0.onset_s]] seconds, persisted for 59.0 [[events.list.0.duration_s]] seconds, recruited 19 [[events.list.0.n_channels]] channels, had a dominant frequency of 4.5 [[events.list.0.dominant_freq_hz]] Hz, and showed a peak z-score of 12.23 [[events.list.0.peak_z]].
- `events.list.0.onset_s` = 21.0: when this candidate starts (seconds from the start).
- `events.list.0.duration_s` = 59.0: how long this candidate lasts (seconds).
- `events.list.0.n_channels` = 19: channels where the candidate was seen.
- `events.list.0.dominant_freq_hz` = 4.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.0.peak_z` = 12.2318: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

> The subsequent seizure-like event began at 168.0 [[events.list.1.onset_s]] seconds, lasted 57.0 [[events.list.1.duration_s]] seconds across 19 [[events.list.1.n_channels]] channels, had a dominant frequency of 2.5 [[events.list.1.dominant_freq_hz]] Hz, and reached a peak z-score of 13.30 [[events.list.1.peak_z]].
- `events.list.1.onset_s` = 168.0: when this candidate starts (seconds from the start).
- `events.list.1.duration_s` = 57.0: how long this candidate lasts (seconds).
- `events.list.1.n_channels` = 19: channels where the candidate was seen.
- `events.list.1.dominant_freq_hz` = 2.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.1.peak_z` = 13.2973: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

## A05

> ### Summary

> This analysis is intended for research use only.

> The recording encompasses 19 [[recording.n_channels]] channels evaluated over 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> Aperiodic decomposition demonstrated identifiable oscillatory peaks across 19 [[aperiodic.n_channels_with_alpha]] channels.
- `aperiodic.n_channels_with_alpha` = 19: channels where an alpha peak (7-14 Hz) rises above the 1/f background.

> Global functional connectivity displayed an average phase-locking value of 0.082 [[connectivity.plv_mean]] and a mean debiased weighted phase lag index of 0.0001 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.0820556: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000102531: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> There were 0 [[events.n_events]] seizure-like events observed.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> Data were gathered in a referential montage across 19 [[recording.n_channels]] channels with a sampling rate of 256.0 [[recording.sfreq_hz]] Hz.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> The continuous recording spanned a duration of 300.0 [[recording.duration_s]] seconds.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> ### Quality

> Channel assessment identified 19 [[qc.n_good]] good channels and 0 [[qc.n_bad]] bad channels.
- `qc.n_good` = 19: channels kept after quality control.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Notch filtering shifted the median line noise ratio from 0.337 [[qc.line_noise_ratio_before_median]] down to 0.00005 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.336766: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 4.76001e-05: the same ratio AFTER the 50 Hz notch filter.

> The background spectral parametrization routine succeeded without failure, logging 0 [[aperiodic.n_poor_fits]] poor fits and reaching a mean coefficient of determination of 0.999 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.998907: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Metrics were computed across 299 [[spectral.n_segments]] Fourier segments.
- `spectral.n_segments` = 299: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).

> Mean absolute alpha power was 6.34 [[spectral.alpha_band_power_uv2.mean]] microvolts squared, and relative alpha power averaged 0.063 [[spectral.relative_alpha_power.mean]].
- `spectral.alpha_band_power_uv2.mean` = 6.33801: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0634188: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Conventional band power mixes oscillations with the aperiodic background; peak power above the aperiodic fit is the oscillation measure that isolates genuine rhythmic activity.

> For the 19 [[aperiodic.n_channels_with_alpha]] channels exhibiting an alpha peak, the mean peak frequency was 10.51 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and the mean peak power above the fitted background was 0.47 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 19: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 10.5118: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.473295: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> The underlying aperiodic slope had a mean exponent of 2.07 [[aperiodic.exponent.mean]] and an offset of 1.93 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 2.07134: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.9325: overall height (log10 power) of the 1/f background. (average over channels)

> ### Coupling

> Sensor-level connectivity across 150 [[connectivity.n_epochs]] epochs yielded an average phase-locking value of 0.082 [[connectivity.plv_mean]] and a mean debiased weighted phase lag index of 0.0001 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 150: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.0820556: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000102531: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> PLV is inflated by volume conduction while debiased wPLI is not, making the latter a more conservative index of true non-zero phase lag.

> The strongest phase-lagged interaction occurred between channels P7 and O1, showing a debiased weighted phase lag index of 0.029 [[connectivity.top_pairs.0.dwpli]] and a phase-locking value of 0.109 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0285854: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.109135: PLV of this pair (inflated by volume conduction).

> ### Events

> No sustained high-amplitude or rhythmic patterns were flagged, with 0 [[events.n_events]] seizure-like events detected.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> Consequently, the event rate was 0.0 [[events.rate_per_hour]] per hour and the total event duration was 0.0 [[events.total_duration_s]] seconds.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A06

> ## Summary

> This analysis is provided for research use only.

> The pipeline processed an electrophysiological recording containing 19 [[recording.n_channels]] channels across a duration of 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> Spectral decomposition separated periodic rhythms from aperiodic background activity, functional connectivity was assessed, and 1 [[events.n_events]] seizure-like event was identified.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ## Recording

> The dataset comprises referential montage data acquired across 19 [[recording.n_channels]] channels at a sampling rate of 256.0 [[recording.sfreq_hz]] Hz.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> The total recording length was 300.0 [[recording.duration_s]] seconds.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> ## Quality

> Data quality screening identified 19 [[qc.n_good]] good channels and 0 [[qc.n_bad]] bad channels.
- `qc.n_good` = 19: channels kept after quality control.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Notch filtering reduced the median line noise ratio from 0.69 [[qc.line_noise_ratio_before_median]] to 0.000025 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.685766: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 2.50834e-05: the same ratio AFTER the 50 Hz notch filter.

> Parameterization of the spectral background was successful across the montage, resulting in 0 [[aperiodic.n_poor_fits]] poor fits.
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.

> ## Spectrum

> Standard band power mixes oscillations with the aperiodic background, whereas peak power above the aperiodic fit serves as the true oscillation measure.

> Across 265 [[spectral.n_segments]] evaluated segments, the mean broadband alpha power was 2.87 [[spectral.alpha_band_power_uv2.mean]] microvolts squared, and relative alpha power averaged 0.06 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 265: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 2.87022: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0570418: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Aperiodic parameterization yielded an average exponent of 1.90 [[aperiodic.exponent.mean]], an average offset of 1.47 [[aperiodic.offset.mean]], and a mean model fit R-squared of 0.996 [[aperiodic.r_squared.mean]].
- `aperiodic.exponent.mean` = 1.89742: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.46612: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.r_squared.mean` = 0.996323: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> Distinct oscillatory alpha peaks were resolved in 17 [[aperiodic.n_channels_with_alpha]] channels, showing a mean peak frequency of 10.70 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean peak power above the aperiodic fit of 0.40 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 17: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 10.7006: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.398066: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ## Coupling

> Sensor-level phase interactions were evaluated across 133 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 133: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> The overall mean phase-locking value was 0.087 [[connectivity.plv_mean]], and the mean debiased weighted phase lag index was 0.00028 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.086923: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000280988: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> Phase-locking value is inflated by volume conduction, while debiased weighted phase lag index is not due to its attenuation of zero-lag phase interactions.

> The strongest debiased coupling occurred between channel F7 and channel C4 at 0.031 [[connectivity.top_pairs.0.dwpli]].
- `connectivity.top_pairs.0.dwpli` = 0.0308218: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.

> ## Events

> The pipeline detected 1 [[events.n_events]] seizure-like event, yielding an event rate of 12.0 [[events.rate_per_hour]] per hour and a total event duration of 33.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 12.0: candidates per hour of recording.
- `events.total_duration_s` = 33.0: total seconds covered by candidates.

> The event began at 145.0 [[events.list.0.onset_s]] seconds and ended at 178.0 [[events.list.0.offset_s]] seconds, spanning 33.0 [[events.list.0.duration_s]] seconds across 19 [[events.list.0.n_channels]] channels.
- `events.list.0.onset_s` = 145.0: when this candidate starts (seconds from the start).
- `events.list.0.offset_s` = 178.0: when this candidate ends (seconds).
- `events.list.0.duration_s` = 33.0: how long this candidate lasts (seconds).
- `events.list.0.n_channels` = 19: channels where the candidate was seen.

> It exhibited a dominant frequency of 4.5 [[events.list.0.dominant_freq_hz]] Hz and reached a peak z-score of 15.06 [[events.list.0.peak_z]].
- `events.list.0.dominant_freq_hz` = 4.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.0.peak_z` = 15.0638: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

## A07

> ### Summary

> This report is intended for research use only.

> The dataset comprises 19 [[recording.n_channels]] channels recorded across 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> Preprocessing identified 18 [[qc.n_good]] good channels and 1 [[qc.n_bad]] bad channel.
- `qc.n_good` = 18: channels kept after quality control.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Robust aperiodic fitting was achieved across 18 [[aperiodic.n_channels_with_alpha]] channels.
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.

> Overall phase coupling across 150 [[connectivity.n_epochs]] epochs remained low, and analysis detected 0 [[events.n_events]] seizure-like events.
- `connectivity.n_epochs` = 150: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> The recording was acquired in a referential montage with a sampling frequency of 256.0 [[recording.sfreq_hz]] Hz across 19 [[recording.n_channels]] channels, spanning a duration of 300.0 [[recording.duration_s]] seconds.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> ### Quality

> Quality screening identified 1 [[qc.n_bad]] bad channel, Cz, which was flat for 299.996 [[qc.flat.Cz]] seconds, leaving 18 [[qc.n_good]] valid channels.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.flat.Cz` = 299.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.n_good` = 18: channels kept after quality control.

> Preprocessing reduced median line noise from 0.379872 [[qc.line_noise_ratio_before_median]] to 0.000304026 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.379872: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000304026: the same ratio AFTER the 50 Hz notch filter.

> Model fitting showed 0 [[aperiodic.n_poor_fits]] poor fits, with an average spectral fit R-squared of 0.997 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.997: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Evaluated over 299 [[spectral.n_segments]] segments, mean alpha band power was 10.2304 [[spectral.alpha_band_power_uv2.mean]], peaking at channel C3 with 21.5827 [[spectral.alpha_band_power_uv2.max]], and mean relative alpha power was 0.0949313 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 299: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 10.2304: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.alpha_band_power_uv2.max` = 21.5827: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (highest channel)
- `spectral.relative_alpha_power.mean` = 0.0949313: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Traditional band power mixes oscillations with the aperiodic background; peak power above the aperiodic fit is the oscillation measure.

> Aperiodic modeling yielded a mean exponent of 1.43353 [[aperiodic.exponent.mean]] and mean offset of 1.60659 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.43353: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.60659: overall height (log10 power) of the 1/f background. (average over channels)

> An alpha peak was confirmed in 18 [[aperiodic.n_channels_with_alpha]] channels, exhibiting a mean alpha peak frequency of 11.039 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean peak power above the aperiodic fit of 0.363464 [[aperiodic.alpha_peak_power.mean]], with the maximum peak power above the fit reaching 0.580727 [[aperiodic.alpha_peak_power.max]] in channel Fp2.
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 11.039: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.363464: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)
- `aperiodic.alpha_peak_power.max` = 0.580727: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (highest channel)

> ### Coupling

> Connectivity across 150 [[connectivity.n_epochs]] epochs showed a mean phase-locking value (PLV) of 0.0852583 [[connectivity.plv_mean]] and a mean debiased weighted phase lag index (dwPLI) of 0.000434403 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 150: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.0852583: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000434403: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> Notably, PLV is inflated by volume conduction while debiased wPLI is not.

> The strongest dwPLI coupling emerged between T7 and P4 at 0.025261 [[connectivity.top_pairs.0.dwpli]], with a paired PLV of 0.0901367 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.025261: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.0901367: PLV of this pair (inflated by volume conduction).

> ### Events

> No seizure-like events were observed during the recording, yielding 0 [[events.n_events]] events, an event rate of 0.0 [[events.rate_per_hour]] per hour, and 0.0 [[events.total_duration_s]] seconds of total event duration.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A08

> ### Summary

> This summary provides an overview of quantitative metrics generated for research use only.

> The 120.0 [[recording.duration_s]]-second recording across 19 [[recording.n_channels]] channels was evaluated for data quality, spectral properties, functional coupling, and detection of transient rhythmic patterns.
- `recording.duration_s` = 120.0: length of the recording in seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.

> ### Recording

> The referential recording had a duration of 120.0 [[recording.duration_s]] seconds and a sampling rate of 256.0 [[recording.sfreq_hz]] Hz across 19 [[recording.n_channels]] channels.
- `recording.duration_s` = 120.0: length of the recording in seconds.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.n_channels` = 19: number of EEG channels in the file.

> ### Quality

> Channel quality screening classified 17 [[qc.n_good]] channels as good and 2 [[qc.n_bad]] channels as bad.
- `qc.n_good` = 17: channels kept after quality control.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Channel P4 showed flat activity for 119.996 [[qc.flat.P4]] seconds, while channel O1 was flagged as noisy with a ratio of 18.104 [[qc.noisy.O1]].
- `qc.flat.P4` = 119.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.noisy.O1` = 18.104: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.

> Line noise attenuation successfully reduced the median line noise ratio from 0.599 [[qc.line_noise_ratio_before_median]] before filtering to 0.000163 [[qc.line_noise_ratio_after_median]] after filtering.
- `qc.line_noise_ratio_before_median` = 0.598916: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.00016292: the same ratio AFTER the 50 Hz notch filter.

> ### Spectrum

> Band power mixes oscillations with the aperiodic background; peak power above the aperiodic fit is the oscillation measure.

> Aperiodic parameter estimation yielded a mean exponent of 1.47 [[aperiodic.exponent.mean]], a mean offset of 1.22 [[aperiodic.offset.mean]], and a mean fit determination coefficient of 0.987 [[aperiodic.r_squared.mean]].
- `aperiodic.exponent.mean` = 1.46865: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.2197: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.r_squared.mean` = 0.987182: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> Oscillatory alpha peaks were observed in 15 [[aperiodic.n_channels_with_alpha]] channels, with a mean alpha peak frequency of 8.74 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean alpha peak power above the fit of 0.356 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 15: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 8.74316: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.356191: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> Unadjusted alpha band power averaged 3.67 [[spectral.alpha_band_power_uv2.mean]] microvolts squared.
- `spectral.alpha_band_power_uv2.mean` = 3.67236: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)

> ### Coupling

> Connectivity analysis indicated that PLV is inflated by volume conduction while debiased wPLI is not.

> Over 36 [[connectivity.n_epochs]] epochs, the mean PLV was 0.152 [[connectivity.plv_mean]] and the mean debiased wPLI was -0.00128 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 36: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.152222: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = -0.00128001: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> The strongest functional coupling was detected between channel Fz and channel P3, with a debiased wPLI of 0.144 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.208 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.144042: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.207933: PLV of this pair (inflated by volume conduction).

> ### Events

> The pipeline detected 2 [[events.n_events]] seizure-like events, with a cumulative duration of 45.0 [[events.total_duration_s]] seconds and a rate of 60.0 [[events.rate_per_hour]] events per hour.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.total_duration_s` = 45.0: total seconds covered by candidates.
- `events.rate_per_hour` = 60.0: candidates per hour of recording.

> An event occurred at onset 21.0 [[events.list.0.onset_s]] seconds, with a duration of 28.0 [[events.list.0.duration_s]] seconds and a dominant frequency of 3.5 [[events.list.0.dominant_freq_hz]] Hz across 1 [[events.list.0.n_channels]] channel (F8).
- `events.list.0.onset_s` = 21.0: when this candidate starts (seconds from the start).
- `events.list.0.duration_s` = 28.0: how long this candidate lasts (seconds).
- `events.list.0.dominant_freq_hz` = 3.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.0.n_channels` = 1: channels where the candidate was seen.

> Another event began at onset 90.0 [[events.list.1.onset_s]] seconds, lasting 17.0 [[events.list.1.duration_s]] seconds with a dominant frequency of 4.5 [[events.list.1.dominant_freq_hz]] Hz across 9 [[events.list.1.n_channels]] channels.
- `events.list.1.onset_s` = 90.0: when this candidate starts (seconds from the start).
- `events.list.1.duration_s` = 17.0: how long this candidate lasts (seconds).
- `events.list.1.dominant_freq_hz` = 4.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.1.n_channels` = 9: channels where the candidate was seen.

## A09

> ### Summary

> This report provides an automated quantitative analysis of electroencephalographic data for research use only.

> The dataset reflects a 19 [[recording.n_channels]] channel referential recording analyzed across 150 [[connectivity.n_epochs]] connectivity epochs and 299 [[spectral.n_segments]] spectral segments.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `connectivity.n_epochs` = 150: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `spectral.n_segments` = 299: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).

> No seizure-like events were detected during the recording.

> ### Recording

> The recording consists of 19 [[recording.n_channels]] channels sampled at 256.0 [[recording.sfreq_hz]] Hz for a total duration of 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 300.0: length of the recording in seconds.

> The montage is referential, spanning channels including Fp1, Fp2, Fz, Cz, Pz, O1, and O2.

> ### Quality

> Data quality was high, with 0 [[qc.n_bad]] bad channels and 19 [[qc.n_good]] good channels identified.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 19: channels kept after quality control.

> Notch filtering reduced the median line noise ratio from 0.798028 [[qc.line_noise_ratio_before_median]] to 0.000217629 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.798028: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000217629: the same ratio AFTER the 50 Hz notch filter.

> There were 0 [[aperiodic.n_poor_fits]] poor spectral fits, with a mean aperiodic model fit R-squared of 0.998019 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.998019: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Traditional band power mixes true oscillations with the aperiodic background slope, whereas peak power above the aperiodic fit provides a dedicated oscillation measure.

> Across all 19 [[aperiodic.n_channels_with_alpha]] channels showing alpha peaks, the mean alpha peak frequency was 8.3503 [[aperiodic.alpha_peak_freq_hz.mean]] Hz, ranging from 7.8575 [[aperiodic.alpha_peak_freq_hz.min]] Hz to 8.78085 [[aperiodic.alpha_peak_freq_hz.max]] Hz.
- `aperiodic.n_channels_with_alpha` = 19: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 8.3503: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_freq_hz.min` = 7.8575: frequency (Hz) of the alpha peak. (lowest channel)
- `aperiodic.alpha_peak_freq_hz.max` = 8.78085: frequency (Hz) of the alpha peak. (highest channel)

> The mean alpha peak power above the aperiodic component was 0.53632 [[aperiodic.alpha_peak_power.mean]], with a minimum of 0.207571 [[aperiodic.alpha_peak_power.min]] at P3 and a maximum of 0.796325 [[aperiodic.alpha_peak_power.max]] at Cz.
- `aperiodic.alpha_peak_power.mean` = 0.53632: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)
- `aperiodic.alpha_peak_power.min` = 0.207571: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (lowest channel)
- `aperiodic.alpha_peak_power.max` = 0.796325: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (highest channel)

> The aperiodic exponent had a mean of 1.53138 [[aperiodic.exponent.mean]] and an offset mean of 1.40769 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.53138: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.40769: overall height (log10 power) of the 1/f background. (average over channels)

> Mean relative alpha power was 0.137115 [[spectral.relative_alpha_power.mean]].
- `spectral.relative_alpha_power.mean` = 0.137115: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> ### Coupling

> Functional connectivity was evaluated across channels using phase locking value (PLV) and debiased weighted phase lag index (dwPLI).

> While PLV is inflated by volume conduction, debiased wPLI is not because it ignores zero-lag components.

> The mean PLV was 0.0832214 [[connectivity.plv_mean]], while the mean dwPLI was 0.000821014 [[connectivity.dwpli_mean]] (with a mean weighted PLI of 0.0941652 [[connectivity.wpli_mean]]).
- `connectivity.plv_mean` = 0.0832214: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000821014: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.
- `connectivity.wpli_mean` = 0.0941652: plain wPLI averaged over pairs. Ignores zero-lag sync but is biased UPWARD with few epochs (about 0.15 even with no coupling at 60 epochs).

> The channel pair with the highest dwPLI was Fp1–F4 at 0.0330305 [[connectivity.top_pairs.0.dwpli]] (PLV of 0.0701636 [[connectivity.top_pairs.0.plv]]), followed by F8–C4 with a dwPLI of 0.0223401 [[connectivity.top_pairs.1.dwpli]].
- `connectivity.top_pairs.0.dwpli` = 0.0330305: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.0701636: PLV of this pair (inflated by volume conduction).
- `connectivity.top_pairs.1.dwpli` = 0.0223401: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.

> ### Events

> There were 0 [[events.n_events]] seizure-like events observed during the session, yielding an event rate of 0.0 [[events.rate_per_hour]] per hour and a total duration of 0.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A10

> ### Summary

> This summary provides automated EEG analysis for research use only.

> The dataset includes 19 [[recording.n_channels]] channels recorded for 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> There were 0 [[qc.n_bad]] bad channels present, and signal quality was well preserved.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> An alpha rhythm was detected in 19 [[aperiodic.n_channels_with_alpha]] channels, alongside an average aperiodic exponent of 1.5009 [[aperiodic.exponent.mean]].
- `aperiodic.n_channels_with_alpha` = 19: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.exponent.mean` = 1.5009: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)

> Across epochs, debiased weighted phase lag index values remained near zero, and 0 [[events.n_events]] seizure-like events were detected.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> The continuous EEG was recorded with a sampling rate of 256.0 [[recording.sfreq_hz]] Hz for a duration of 120.0 [[recording.duration_s]] seconds in a referential [[recording.montage]] montage across 19 [[recording.n_channels]] channels.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 120.0: length of the recording in seconds.
- `recording.montage` = "referential": 'referential' = each channel against a reference; 'bipolar' = each channel is the difference of two neighbours.
- `recording.n_channels` = 19: number of EEG channels in the file.

> The complete channel layout consisted of Fp1, Fp2, F7, F3, Fz, F4, F8, T7, C3, Cz, C4, T8, P7, P3, Pz, P4, P8, O1, and O2 [[recording.channels]].
- `recording.channels` = ["Fp1", "Fp2", "F7", "F3", "Fz", "F4", "F8", "T7", "C3", "Cz", "C4", "T8", "P7", "P3", "Pz", "P4", "P8", "O1", "O2"]: the channel names in the file.

> ### Quality

> Channel and artifact screenings identified 0 [[qc.n_bad]] bad channels and confirmed 19 [[qc.n_good]] good channels.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 19: channels kept after quality control.

> Median line noise ratio dropped from 1.08516 [[qc.line_noise_ratio_before_median]] before filtering to 0.000213119 [[qc.line_noise_ratio_after_median]] after cleaning.
- `qc.line_noise_ratio_before_median` = 1.08516: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000213119: the same ratio AFTER the 50 Hz notch filter.

> Parameterization of the spectrum showed 0 [[aperiodic.n_poor_fits]] poor fits, with a mean R-squared metric of 0.994556 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.994556: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Standard band power mixes oscillations with the aperiodic background, whereas peak power above the aperiodic fit is the oscillation measure that isolates genuine rhythmic activity.

> Evaluated across 119 [[spectral.n_segments]] segments, mean alpha band power was 5.58418 [[spectral.alpha_band_power_uv2.mean]], with channel values ranging from 3.66302 [[spectral.alpha_band_power_uv2.min]] at O1 to 8.099 [[spectral.alpha_band_power_uv2.max]] at F3.
- `spectral.n_segments` = 119: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 5.58418: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.alpha_band_power_uv2.min` = 3.66302: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (lowest channel)
- `spectral.alpha_band_power_uv2.max` = 8.099: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (highest channel)

> Mean relative alpha power was 0.128191 [[spectral.relative_alpha_power.mean]].
- `spectral.relative_alpha_power.mean` = 0.128191: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> The aperiodic fit yielded a mean exponent of 1.5009 [[aperiodic.exponent.mean]] and a mean offset of 1.18482 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.5009: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.18482: overall height (log10 power) of the 1/f background. (average over channels)

> The isolated alpha oscillation had a mean peak frequency of 8.52141 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean peak power above the aperiodic background of 0.628053 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.alpha_peak_freq_hz.mean` = 8.52141: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.628053: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ### Coupling

> Phase-locking value (PLV) is inflated by volume conduction while debiased wPLI is not.

> Functional connectivity was calculated across 60 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 60: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> The mean PLV was 0.119896 [[connectivity.plv_mean]], whereas the debiased wPLI mean was -0.000799617 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.119896: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = -0.000799617: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> The channel pair with the strongest coupling was Fp1 and C3, which reached a dwPLI of 0.069721 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.137077 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.069721: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.137077: PLV of this pair (inflated by volume conduction).

> ### Events

> A total of 0 [[events.n_events]] seizure-like events occurred during the recording session, resulting in an event rate of 0.0 [[events.rate_per_hour]] per hour and 0.0 [[events.total_duration_s]] seconds of total event duration.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A11

> ## Summary

> This report is for research use only.

> The dataset consists of 120.0 [[recording.duration_s]] seconds of EEG data recorded across 19 [[recording.n_channels]] channels.
- `recording.duration_s` = 120.0: length of the recording in seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.

> Quality control flagged 2 [[qc.n_bad]] bad channels, leaving 17 [[qc.n_good]] channels for analysis.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 17: channels kept after quality control.

> Spectral analysis evaluated both periodic oscillations and aperiodic backgrounds, functional coupling was quantified, and 0 [[events.n_events]] seizure-like events were detected.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ## Recording

> The recording used a referential montage lasting 120.0 [[recording.duration_s]] seconds with 19 [[recording.n_channels]] channels sampled at 256.0 [[recording.sfreq_hz]] Hz.
- `recording.duration_s` = 120.0: length of the recording in seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> ## Quality

> Data quality screening detected 2 [[qc.n_bad]] bad channels.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Channel P8 was flat for 119.996 [[qc.flat.P8]] seconds, and channel Fp2 showed high noise with a ratio of 12.23 [[qc.noisy.Fp2]].
- `qc.flat.P8` = 119.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.noisy.Fp2` = 12.226: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.

> Median line noise ratio improved from 0.42 [[qc.line_noise_ratio_before_median]] before cleaning to 0.001 [[qc.line_noise_ratio_after_median]] after cleaning, leaving 17 [[qc.n_good]] clean channels for further analysis.
- `qc.line_noise_ratio_before_median` = 0.419677: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000974557: the same ratio AFTER the 50 Hz notch filter.
- `qc.n_good` = 17: channels kept after quality control.

> ## Spectrum

> Standard band power mixes oscillations with the aperiodic background (peak power above the aperiodic fit is the oscillation measure).

> Across 119 [[spectral.n_segments]] segments, mean alpha band power was 8.94 [[spectral.alpha_band_power_uv2.mean]] microvolts squared, and mean relative alpha power was 0.086 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 119: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 8.93572: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0863459: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Aperiodic fitting yielded a mean R-squared of 0.98 [[aperiodic.r_squared.mean]] with 0 [[aperiodic.n_poor_fits]] poor fits, a mean offset of 1.15 [[aperiodic.offset.mean]], and a mean exponent of 0.87 [[aperiodic.exponent.mean]].
- `aperiodic.r_squared.mean` = 0.98232: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.offset.mean` = 1.14506: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.exponent.mean` = 0.865574: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)

> Distinct alpha oscillations above the background fit were identified in 8 [[aperiodic.n_channels_with_alpha]] channels, showing a mean peak frequency of 8.51 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean peak power of 0.16 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 8: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 8.50799: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.159729: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ## Coupling

> Functional coupling was computed across 60 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 60: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> PLV is inflated by volume conduction while debiased wPLI is not.

> Mean PLV was 0.14 [[connectivity.plv_mean]], and mean debiased wPLI was -0.00024 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.135019: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = -0.000243062: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> The strongest phase coupling occurred between channels Fz and F8, with a debiased wPLI of 0.057 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.17 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0567185: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.169521: PLV of this pair (inflated by volume conduction).

> ## Events

> The pipeline detected 0 [[events.n_events]] seizure-like events, corresponding to an event rate of 0.0 [[events.rate_per_hour]] per hour and 0.0 [[events.total_duration_s]] seconds of total event duration.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A12

> ### Summary

> This report is for research use only.

> The dataset includes 19 [[recording.n_channels]] channels recorded across 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> Artifact assessment marked 1 [[qc.n_bad]] channel as noisy, leaving 18 [[qc.n_good]] clean channels.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 18: channels kept after quality control.

> Analysis detected 0 [[events.n_events]] seizure-like events during the recording.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> Data were acquired with a referential montage at a sampling frequency of 256.0 [[recording.sfreq_hz]] Hz across 19 [[recording.n_channels]] channels.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.n_channels` = 19: number of EEG channels in the file.

> Total continuous recording length was 120.0 [[recording.duration_s]] seconds.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> ### Quality

> Data quality screening identified 1 [[qc.n_bad]] bad channel, P8, which exhibited high variance (noise ratio of 18.61 [[qc.noisy.P8]]), leaving 18 [[qc.n_good]] accepted channels.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.noisy.P8` = 18.61: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.
- `qc.n_good` = 18: channels kept after quality control.

> Preprocessing successfully reduced the median line noise ratio from 0.79 [[qc.line_noise_ratio_before_median]] before filtering down to 0.00037 [[qc.line_noise_ratio_after_median]] after cleaning.
- `qc.line_noise_ratio_before_median` = 0.789202: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000369274: the same ratio AFTER the 50 Hz notch filter.

> ### Spectrum

> Unadjusted band power mixes oscillations with the aperiodic background, whereas peak power above the aperiodic fit is the oscillation measure that isolates true periodic rhythmicity.

> Across 119 [[spectral.n_segments]] segments, mean alpha power was 2.97 [[spectral.alpha_band_power_uv2.mean]], and mean relative alpha power was 0.06 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 119: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 2.97394: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0594067: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Aperiodic decomposition achieved an average fit R-squared of 0.99 [[aperiodic.r_squared.mean]], with a mean exponent of 1.28 [[aperiodic.exponent.mean]] and mean offset of 1.12 [[aperiodic.offset.mean]].
- `aperiodic.r_squared.mean` = 0.991251: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)
- `aperiodic.exponent.mean` = 1.27794: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.12177: overall height (log10 power) of the 1/f background. (average over channels)

> Distinct rhythmic peaks above the aperiodic fit appeared in 2 [[aperiodic.n_channels_with_alpha]] channels (F7 and Pz), with a mean alpha peak frequency of 13.03 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and mean alpha peak power of 0.07 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 2: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 13.0315: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.0676937: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ### Coupling

> Connectivity was quantified over 60 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 60: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> Mean phase locking value (PLV) reached 0.12 [[connectivity.plv_mean]], and mean weighted phase lag index (wPLI) reached 0.15 [[connectivity.wpli_mean]].
- `connectivity.plv_mean` = 0.12085: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.wpli_mean` = 0.145511: plain wPLI averaged over pairs. Ignores zero-lag sync but is biased UPWARD with few epochs (about 0.15 even with no coupling at 60 epochs).

> PLV is inflated by volume conduction while debiased wPLI is not.

> The debiased wPLI averaged -0.000046 [[connectivity.dwpli_mean]] overall.
- `connectivity.dwpli_mean` = -4.56296e-05: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> The highest coupling was observed between F7 and F4, showing a debiased wPLI of 0.09 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.17 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0886581: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.167054: PLV of this pair (inflated by volume conduction).

> ### Events

> No seizure-like events were detected in the signal, giving 0 [[events.n_events]] events, an event rate of 0.0 [[events.rate_per_hour]] per hour, and 0.0 [[events.total_duration_s]] seconds of total event duration.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A13

> ### Summary

> This analysis summarizes electrophysiological metrics processed for research use only.

> The referential recording comprises 19 [[recording.n_channels]] channels over a duration of 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> Data quality was high with 0 [[qc.n_bad]] bad channels.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Analysis identified oscillatory activity alongside aperiodic background components, low overall phase synchronization, and 1 [[events.n_events]] seizure-like event.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> The dataset was collected in a referential montage across 19 [[recording.n_channels]] channels with a sampling rate of 256.0 [[recording.sfreq_hz]] Hz for a total duration of 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 120.0: length of the recording in seconds.

> ### Quality

> Data cleaning retained 19 [[qc.n_good]] channels and identified 0 [[qc.n_bad]] channels requiring rejection.
- `qc.n_good` = 19: channels kept after quality control.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Median line noise ratio decreased from 0.48 [[qc.line_noise_ratio_before_median]] before filtering to 0.0001 [[qc.line_noise_ratio_after_median]] after filtering.
- `qc.line_noise_ratio_before_median` = 0.483957: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 9.96147e-05: the same ratio AFTER the 50 Hz notch filter.

> Spectral parameterization demonstrated robust fitting, with 0 [[aperiodic.n_poor_fits]] poor fits and a mean model fit R-squared of 0.99 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.993226: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Standard band power mixes oscillations with the aperiodic background; therefore, peak power above the aperiodic fit is the oscillation measure.

> Parameterized alpha peaks appeared across 19 [[aperiodic.n_channels_with_alpha]] channels, displaying a mean alpha peak frequency of 9.22 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean peak power of 0.78 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 19: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 9.21832: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.782999: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> The underlying aperiodic slope exhibited a mean exponent of 1.47 [[aperiodic.exponent.mean]] and an offset of 1.44 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.4706: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.44173: overall height (log10 power) of the 1/f background. (average over channels)

> Across 68 [[spectral.n_segments]] segments, mean alpha band power measured 18.39 [[spectral.alpha_band_power_uv2.mean]] µV², with a mean relative alpha power of 0.22 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 68: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 18.3937: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.223604: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> ### Coupling

> Connectivity was evaluated over 34 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 34: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> Mean phase-locking value (PLV) reached 0.16 [[connectivity.plv_mean]], whereas mean debiased weighted phase lag index (dwPLI) was -0.0026 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.155057: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = -0.00256171: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> PLV is inflated by volume conduction while debiased wPLI is not.

> The pair with the highest dwPLI comprised channels F7 and P7, with a dwPLI of 0.19 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.24 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.188402: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.235828: PLV of this pair (inflated by volume conduction).

> ### Events

> The recording contained 1 [[events.n_events]] seizure-like event, yielding a rate of 30.0 [[events.rate_per_hour]] per hour and a total duration of 50.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 1: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 30.0: candidates per hour of recording.
- `events.total_duration_s` = 50.0: total seconds covered by candidates.

> This event began at 49.0 [[events.list.0.onset_s]] seconds and concluded at 99.0 [[events.list.0.offset_s]] seconds (duration of 50.0 [[events.list.0.duration_s]] seconds).
- `events.list.0.onset_s` = 49.0: when this candidate starts (seconds from the start).
- `events.list.0.offset_s` = 99.0: when this candidate ends (seconds).
- `events.list.0.duration_s` = 50.0: how long this candidate lasts (seconds).

> It involved 3 [[events.list.0.n_channels]] channels (Fz, F4, F8) with a dominant frequency of 3.0 [[events.list.0.dominant_freq_hz]] Hz and a peak z-score of 1.79 [[events.list.0.peak_z]].
- `events.list.0.n_channels` = 3: channels where the candidate was seen.
- `events.list.0.dominant_freq_hz` = 3.0: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.0.peak_z` = 1.79423: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

## A14

> ### Summary

> This pipeline output is for research use only.

> The dataset includes 19 [[recording.n_channels]] channels recorded over 300.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.

> Data screening identified 1 [[qc.n_bad]] noisy channel, leaving 18 [[qc.n_good]] channels for evaluation.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 18: channels kept after quality control.

> Spectral parameterization showed an average alpha peak frequency of 11.02 [[aperiodic.alpha_peak_freq_hz.mean]] Hz.
- `aperiodic.alpha_peak_freq_hz.mean` = 11.0166: frequency (Hz) of the alpha peak. (average over channels)

> Functional connectivity yielded a mean debiased weighted phase lag index of -0.0013 [[connectivity.dwpli_mean]].
- `connectivity.dwpli_mean` = -0.00125143: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> In total, 2 [[events.n_events]] seizure-like events were detected across the recording.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> The session contains 19 [[recording.n_channels]] channels recorded for 300.0 [[recording.duration_s]] seconds at a sampling frequency of 256.0 [[recording.sfreq_hz]] Hz using a referential montage.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 300.0: length of the recording in seconds.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> ### Quality

> Channel evaluation identified 1 [[qc.n_bad]] channel with excessive noise, F4, showing a noise ratio of 48.17 [[qc.noisy.F4]], while 18 [[qc.n_good]] channels met quality criteria.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.noisy.F4` = 48.167: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.
- `qc.n_good` = 18: channels kept after quality control.

> The median line noise ratio decreased from 0.042 [[qc.line_noise_ratio_before_median]] to 0.000011 [[qc.line_noise_ratio_after_median]] following notch filtering.
- `qc.line_noise_ratio_before_median` = 0.0423572: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 1.10754e-05: the same ratio AFTER the 50 Hz notch filter.

> Aperiodic model fitting had 0 [[aperiodic.n_poor_fits]] poor fits.
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.

> ### Spectrum

> Across 203 [[spectral.n_segments]] segments, alpha band power averaged 7.91 [[spectral.alpha_band_power_uv2.mean]] μV² with a relative alpha power of 0.083 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 203: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 7.90602: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0827811: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Standard band power mixes oscillations with the aperiodic background; peak power above the aperiodic fit is the oscillation measure.

> Across 18 [[aperiodic.n_channels_with_alpha]] channels exhibiting alpha peaks, the mean exponent was 1.79 [[aperiodic.exponent.mean]], the mean offset was 1.79 [[aperiodic.offset.mean]], the mean alpha peak frequency was 11.02 [[aperiodic.alpha_peak_freq_hz.mean]] Hz, and the mean alpha peak power above the fit was 0.38 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.exponent.mean` = 1.79022: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.7854: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.alpha_peak_freq_hz.mean` = 11.0166: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.381467: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ### Coupling

> Connectivity was calculated over 102 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 102: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> The mean phase-locking value was 0.096 [[connectivity.plv_mean]], and the mean debiased weighted phase lag index was -0.0013 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.0955767: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = -0.00125143: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> PLV is inflated by volume conduction while debiased wPLI is not.

> The pair with the highest debiased wPLI was Cz and Pz, which showed a debiased wPLI of 0.041 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.100 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0411763: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.0998327: PLV of this pair (inflated by volume conduction).

> ### Events

> The detection process marked 2 [[events.n_events]] seizure-like events, corresponding to a rate of 24.0 [[events.rate_per_hour]] per hour and a cumulative duration of 94.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 24.0: candidates per hour of recording.
- `events.total_duration_s` = 94.0: total seconds covered by candidates.

> An event started at 38.0 [[events.list.0.onset_s]] seconds, lasting 59.0 [[events.list.0.duration_s]] seconds across 17 [[events.list.0.n_channels]] channels with a dominant frequency of 4.0 [[events.list.0.dominant_freq_hz]] Hz.
- `events.list.0.onset_s` = 38.0: when this candidate starts (seconds from the start).
- `events.list.0.duration_s` = 59.0: how long this candidate lasts (seconds).
- `events.list.0.n_channels` = 17: channels where the candidate was seen.
- `events.list.0.dominant_freq_hz` = 4.0: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.

> Another event started at 186.0 [[events.list.1.onset_s]] seconds, lasting 35.0 [[events.list.1.duration_s]] seconds across 18 [[events.list.1.n_channels]] channels with a dominant frequency of 2.5 [[events.list.1.dominant_freq_hz]] Hz.
- `events.list.1.onset_s` = 186.0: when this candidate starts (seconds from the start).
- `events.list.1.duration_s` = 35.0: how long this candidate lasts (seconds).
- `events.list.1.n_channels` = 18: channels where the candidate was seen.
- `events.list.1.dominant_freq_hz` = 2.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.

## A15

> ## Summary

> This summary is for research use only.

> The pipeline processed 19 [[recording.n_channels]] channels across 120.0 [[recording.duration_s]] seconds of recording time.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> Overall data quality was strong, presenting 0 [[qc.n_bad]] bad channels.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> There were 0 [[events.n_events]] seizure-like events observed during the session.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ## Recording

> The recording was acquired with 19 [[recording.n_channels]] channels using a referential [[recording.montage]] montage.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.montage` = "referential": 'referential' = each channel against a reference; 'bipolar' = each channel is the difference of two neighbours.

> The sampling rate was 256.0 [[recording.sfreq_hz]] Hz, yielding a total analyzed duration of 120.0 [[recording.duration_s]] seconds.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 120.0: length of the recording in seconds.

> ## Quality

> Electrode quality checks identified 19 [[qc.n_good]] good channels and 0 [[qc.n_bad]] bad channels.
- `qc.n_good` = 19: channels kept after quality control.
- `qc.n_bad` = 0: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Notch filtering successfully attenuated electrical interference, reducing the median line noise ratio from 0.29 [[qc.line_noise_ratio_before_median]] to 0.00056 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.286093: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000563451: the same ratio AFTER the 50 Hz notch filter.

> Across the montage, there were 0 [[aperiodic.n_poor_fits]] poor spectral fits.
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.

> ## Spectrum

> Across 119 [[spectral.n_segments]] segments, mean alpha band power was 38.78 [[spectral.alpha_band_power_uv2.mean]] μV², with an average relative power of 0.25 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 119: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 38.7776: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.250645: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Unadjusted band power mixes oscillations with the aperiodic background, meaning that peak power above the aperiodic fit is the oscillation measure to assess true rhythmic activity.

> Modeling the aperiodic background yielded an average exponent of 0.94 [[aperiodic.exponent.mean]] and an offset of 1.20 [[aperiodic.offset.mean]], with a mean model fit R² of 0.99 [[aperiodic.r_squared.mean]].
- `aperiodic.exponent.mean` = 0.941259: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.2019: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.r_squared.mean` = 0.993529: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> Alpha peaks were identified in 19 [[aperiodic.n_channels_with_alpha]] channels, displaying a mean frequency of 8.73 [[aperiodic.alpha_peak_freq_hz.mean]] Hz (ranging from 7.75 [[aperiodic.alpha_peak_freq_hz.min]] Hz to 9.59 [[aperiodic.alpha_peak_freq_hz.max]] Hz) and a mean peak power of 0.88 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 19: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 8.72994: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_freq_hz.min` = 7.75375: frequency (Hz) of the alpha peak. (lowest channel)
- `aperiodic.alpha_peak_freq_hz.max` = 9.58793: frequency (Hz) of the alpha peak. (highest channel)
- `aperiodic.alpha_peak_power.mean` = 0.876219: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ## Coupling

> Phase synchronization over 60 [[connectivity.n_epochs]] epochs resulted in a mean phase-locking value (PLV) of 0.12 [[connectivity.plv_mean]], an average weighted phase lag index (wPLI) of 0.14 [[connectivity.wpli_mean]], and a mean debiased wPLI (dwPLI) of 0.00080 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 60: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.121755: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.wpli_mean` = 0.144734: plain wPLI averaged over pairs. Ignores zero-lag sync but is biased UPWARD with few epochs (about 0.15 even with no coupling at 60 epochs).
- `connectivity.dwpli_mean` = 0.000802637: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> It should be noted that PLV is inflated by volume conduction while debiased wPLI is not.

> The highest dwPLI connection occurred between channel F3 and channel P4 with a dwPLI of 0.074 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.14 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0738497: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.144382: PLV of this pair (inflated by volume conduction).

> ## Events

> No transient high-line-length patterns were detected, resulting in 0 [[events.n_events]] seizure-like events, an event rate of 0.0 [[events.rate_per_hour]] per hour, and 0.0 [[events.total_duration_s]] seconds of total event duration.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A16

> ### Summary

> This analysis is for research use only.

> The dataset includes 19 [[recording.n_channels]] channels evaluated over 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> Parameterization of the spectrum showed an average aperiodic exponent of 2.10 [[aperiodic.exponent.mean]].
- `aperiodic.exponent.mean` = 2.09726: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)

> Functional coupling assessed across 37 [[connectivity.n_epochs]] epochs yielded an average phase-locking value of 0.15 [[connectivity.plv_mean]] and a debiased weighted phase lag index of 0.00039 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 37: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.15228: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000389458: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> The pipeline detected 2 [[events.n_events]] seizure-like events.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> The recording consists of 19 [[recording.n_channels]] channels sampled at 256.0 [[recording.sfreq_hz]] Hz for a total duration of 120.0 [[recording.duration_s]] seconds using a referential montage.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.duration_s` = 120.0: length of the recording in seconds.

> ### Quality

> Data inspection identified 18 [[qc.n_good]] good channels and 1 [[qc.n_bad]] bad channel.
- `qc.n_good` = 18: channels kept after quality control.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Channel Pz was marked bad after displaying flat signal for 120.0 [[qc.flat.Pz]] seconds.
- `qc.flat.Pz` = 119.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.

> Line noise cleaning shifted the median noise ratio from 0.61 [[qc.line_noise_ratio_before_median]] to 0.0000073 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.609704: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 7.33315e-06: the same ratio AFTER the 50 Hz notch filter.

> The spectral fitting algorithm produced 0 [[aperiodic.n_poor_fits]] poor fits.
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.

> ### Spectrum

> Across 73 [[spectral.n_segments]] segments, mean absolute alpha band power was 4.40 [[spectral.alpha_band_power_uv2.mean]], and mean relative alpha power was 0.064 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 73: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 4.40196: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0640171: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Standard band power mixes oscillations with the aperiodic background, whereas peak power above the aperiodic fit is the oscillation measure.

> Parameterizing the background yielded an aperiodic offset mean of 1.63 [[aperiodic.offset.mean]], an exponent mean of 2.10 [[aperiodic.exponent.mean]], and a fit determination coefficient of 1.00 [[aperiodic.r_squared.mean]].
- `aperiodic.offset.mean` = 1.62544: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.exponent.mean` = 2.09726: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.r_squared.mean` = 0.995906: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> Distinct alpha peaks were present in 18 [[aperiodic.n_channels_with_alpha]] channels, averaging a peak frequency of 8.93 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and an oscillation peak power of 0.74 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 8.93467: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.735491: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ### Coupling

> Functional connectivity was measured across 37 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 37: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> The overall mean phase-locking value was 0.15 [[connectivity.plv_mean]], and the mean debiased weighted phase lag index was 0.00039 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.15228: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000389458: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> Phase-locking value is inflated by volume conduction while debiased wPLI is not.

> The pair C3 and O1 showed strong coupling, with a phase-locking value of 0.24 [[connectivity.top_pairs.0.plv]] and a debiased weighted phase lag index of 0.18 [[connectivity.top_pairs.0.dwpli]].
- `connectivity.top_pairs.0.plv` = 0.240569: PLV of this pair (inflated by volume conduction).
- `connectivity.top_pairs.0.dwpli` = 0.175383: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.

> ### Events

> The recording contained 2 [[events.n_events]] seizure-like events, representing an event rate of 60.0 [[events.rate_per_hour]] per hour and a cumulative duration of 44.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 60.0: candidates per hour of recording.
- `events.total_duration_s` = 44.0: total seconds covered by candidates.

> The first seizure-like event started at 10.0 [[events.list.0.onset_s]] seconds, lasting 19.0 [[events.list.0.duration_s]] seconds across 18 [[events.list.0.n_channels]] channels with a peak z-score of 6.90 [[events.list.0.peak_z]] and a dominant frequency of 3.0 [[events.list.0.dominant_freq_hz]] Hz.
- `events.list.0.onset_s` = 10.0: when this candidate starts (seconds from the start).
- `events.list.0.duration_s` = 19.0: how long this candidate lasts (seconds).
- `events.list.0.n_channels` = 18: channels where the candidate was seen.
- `events.list.0.peak_z` = 6.89654: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.
- `events.list.0.dominant_freq_hz` = 3.0: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.

> The second seizure-like event began at 71.0 [[events.list.1.onset_s]] seconds, spanning 25.0 [[events.list.1.duration_s]] seconds over 16 [[events.list.1.n_channels]] channels with a dominant frequency of 4.5 [[events.list.1.dominant_freq_hz]] Hz and a peak z-score of 4.47 [[events.list.1.peak_z]].
- `events.list.1.onset_s` = 71.0: when this candidate starts (seconds from the start).
- `events.list.1.duration_s` = 25.0: how long this candidate lasts (seconds).
- `events.list.1.n_channels` = 16: channels where the candidate was seen.
- `events.list.1.dominant_freq_hz` = 4.5: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.1.peak_z` = 4.47141: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

## A17

> ## Summary

> This report summarizes quantitative electroencephalogram metrics provided for research use only.

> Across the recording, 17 [[qc.n_good]] channels were preserved following artifact screening that excluded 2 [[qc.n_bad]] bad channels.
- `qc.n_good` = 17: channels kept after quality control.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Spectral decomposition revealed robust aperiodic fits across channels, permitting isolated assessment of alpha oscillations.

> Sensor-level functional coupling metrics indicated minimal phase synchrony, and 0 [[events.n_events]] seizure-like events were detected.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ## Recording

> The recording spanned a total duration of 300.0 [[recording.duration_s]] seconds with a sampling frequency of 256.0 [[recording.sfreq_hz]] Hz.
- `recording.duration_s` = 300.0: length of the recording in seconds.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> Data acquisition utilized 19 [[recording.n_channels]] channels in a referential montage.
- `recording.n_channels` = 19: number of EEG channels in the file.

> ## Quality

> Data quality checks identified 2 [[qc.n_bad]] bad channels, leaving 17 [[qc.n_good]] channels for further evaluation.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 17: channels kept after quality control.

> Channel F7 was flagged as flat for 299.996 [[qc.flat.F7]] seconds, and channel P8 was marked as noisy with an amplitude deviation ratio of 34.255 [[qc.noisy.P8]].
- `qc.flat.F7` = 299.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.noisy.P8` = 34.255: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.

> Line noise reduction decreased the median noise ratio from 0.552248 [[qc.line_noise_ratio_before_median]] to 0.00014052 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.552248: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.00014052: the same ratio AFTER the 50 Hz notch filter.

> ## Spectrum

> Standard band power mixes oscillations with the aperiodic background, whereas peak power above the aperiodic fit isolates true oscillatory activity.

> The mean alpha band power was 10.896 [[spectral.alpha_band_power_uv2.mean]] with a relative alpha power of 0.130757 [[spectral.relative_alpha_power.mean]].
- `spectral.alpha_band_power_uv2.mean` = 10.896: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.130757: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Aperiodic background parameterization showed an average spectral exponent of 1.61009 [[aperiodic.exponent.mean]] and an offset of 1.53721 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.61009: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.53721: overall height (log10 power) of the 1/f background. (average over channels)

> Prominent alpha peaks were present in 17 [[aperiodic.n_channels_with_alpha]] channels, exhibiting an average peak frequency of 11.7196 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and an average peak power above the aperiodic fit of 0.898653 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.n_channels_with_alpha` = 17: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 11.7196: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.898653: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> Spectral models fit cleanly, with 0 [[aperiodic.n_poor_fits]] poor fits and a mean R-squared of 0.997409 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.997409: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ## Coupling

> Connectivity was calculated over 150 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 150: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> When evaluating phase relations, phase-locking value (PLV) is inflated by volume conduction while debiased weighted phase lag index (dwPLI) is not.

> Global average PLV was 0.0847229 [[connectivity.plv_mean]], average weighted phase lag index was 0.089516 [[connectivity.wpli_mean]], and mean dwPLI was -0.000694674 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.0847229: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.wpli_mean` = 0.089516: plain wPLI averaged over pairs. Ignores zero-lag sync but is biased UPWARD with few epochs (about 0.15 even with no coupling at 60 epochs).
- `connectivity.dwpli_mean` = -0.000694674: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> The strongest dwPLI coupling was observed between channel Cz and channel P4 at 0.0208361 [[connectivity.top_pairs.0.dwpli]], with a corresponding PLV of 0.0958009 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0208361: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.0958009: PLV of this pair (inflated by volume conduction).

> ## Events

> No sustained rhythmic activity was identified by the event detection pipeline, yielding 0 [[events.n_events]] seizure-like events, an hourly rate of 0.0 [[events.rate_per_hour]], and an event duration of 0.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A18

> ### Summary

> This report summarizes quantitative metrics from an electroencephalographic recording for research use only.

> The pipeline processed 18 [[qc.n_good]] usable channels after excluding non-functional sensors.
- `qc.n_good` = 18: channels kept after quality control.

> Spectral parameterization identified alpha rhythms across 18 [[aperiodic.n_channels_with_alpha]] channels, yielding a mean aperiodic exponent of 2.13 [[aperiodic.exponent.mean]].
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.exponent.mean` = 2.12626: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)

> Phase coupling metrics were estimated over 60 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 60: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> ### Recording

> The dataset contains 19 [[recording.n_channels]] electrodes recorded with a referential montage at a sampling rate of 256.0 [[recording.sfreq_hz]] Hz.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> The total recording time was 120.0 [[recording.duration_s]] seconds.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> ### Quality

> Channel quality inspection flagged 1 [[qc.n_bad]] bad channel due to flat activity on P4 for 120.0 [[qc.flat.P4]] seconds, leaving 18 [[qc.n_good]] channels for downstream analysis.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.flat.P4` = 119.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.n_good` = 18: channels kept after quality control.

> Filtering reduced the median line noise ratio from 0.17 [[qc.line_noise_ratio_before_median]] to 0.0000057 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 0.171896: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 5.71102e-06: the same ratio AFTER the 50 Hz notch filter.

> Aperiodic fitting was reliable across the montage, showing 0 [[aperiodic.n_poor_fits]] poor fits and an average r-squared of 1.00 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.996088: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Across 119 [[spectral.n_segments]] segments, mean absolute alpha band power was 22.56 [[spectral.alpha_band_power_uv2.mean]], with channel values ranging from 7.85 [[spectral.alpha_band_power_uv2.min]] at F3 to 81.49 [[spectral.alpha_band_power_uv2.max]] at O2, while mean relative alpha power was 0.06 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 119: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 22.56: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.alpha_band_power_uv2.min` = 7.84643: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (lowest channel)
- `spectral.alpha_band_power_uv2.max` = 81.4902: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (highest channel)
- `spectral.relative_alpha_power.mean` = 0.0647082: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Traditional band power mixes oscillations with the aperiodic background (peak power above the aperiodic fit is the oscillation measure).

> Following separation of background activity from rhythms, the alpha peak frequency averaged 9.49 [[aperiodic.alpha_peak_freq_hz.mean]] Hz, with a peak power above the aperiodic fit of 1.31 [[aperiodic.alpha_peak_power.mean]].
- `aperiodic.alpha_peak_freq_hz.mean` = 9.48536: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 1.31107: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> The aperiodic background had a mean offset of 1.39 [[aperiodic.offset.mean]] and an exponent of 2.13 [[aperiodic.exponent.mean]].
- `aperiodic.offset.mean` = 1.39004: overall height (log10 power) of the 1/f background. (average over channels)
- `aperiodic.exponent.mean` = 2.12626: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)

> ### Coupling

> Functional connectivity was evaluated across 60 [[connectivity.n_epochs]] epochs.
- `connectivity.n_epochs` = 60: number of 2-second pieces used to estimate coupling; more epochs = more reliable.

> The overall mean phase locking value was 0.21 [[connectivity.plv_mean]], and the mean debiased weighted phase lag index was 0.002 [[connectivity.dwpli_mean]].
- `connectivity.plv_mean` = 0.210524: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.00228619: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> PLV is inflated by volume conduction while debiased wPLI is not, because debiased wPLI reduces zero-lag phase effects.

> The strongest debiased weighted phase lag index values appeared between Cz and Pz at 0.09 [[connectivity.top_pairs.0.dwpli]], as well as C3 and Cz at 0.08 [[connectivity.top_pairs.1.dwpli]].
- `connectivity.top_pairs.0.dwpli` = 0.0854479: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.1.dwpli` = 0.0836481: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.

> ### Events

> Event detection based on line length identified 0 [[events.n_events]] seizure-like events.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> The corresponding event rate was 0.0 [[events.rate_per_hour]] per hour, and total event duration was 0.0 [[events.total_duration_s]] seconds.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A19

> ### Summary

> This EEG analysis pipeline output is intended for research use only.

> The dataset contains 19 [[recording.n_channels]] channels recorded for 120.0 [[recording.duration_s]] seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> Data quality is strong overall, featuring 18 [[qc.n_good]] usable channels and 0 [[events.n_events]] seizure-like events.
- `qc.n_good` = 18: channels kept after quality control.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.

> ### Recording

> The recording was sampled at 256.0 [[recording.sfreq_hz]] Hz across 19 [[recording.n_channels]] scalp channels arranged in a referential montage.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).
- `recording.n_channels` = 19: number of EEG channels in the file.

> The total length of the recorded session was 120.0 [[recording.duration_s]] seconds.
- `recording.duration_s` = 120.0: length of the recording in seconds.

> ### Quality

> Pre-processing detected 1 [[qc.n_bad]] bad channel due to high noise, specifically F4, leaving 18 [[qc.n_good]] clean channels.
- `qc.n_bad` = 1: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 18: channels kept after quality control.

> Notch filtering lowered the median line noise ratio from 1.48439 [[qc.line_noise_ratio_before_median]] to 0.0000433 [[qc.line_noise_ratio_after_median]].
- `qc.line_noise_ratio_before_median` = 1.48439: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 4.33126e-05: the same ratio AFTER the 50 Hz notch filter.

> Parameterization of the spectrum showed high reliability, with 0 [[aperiodic.n_poor_fits]] poor fits and a mean model fit R-squared of 0.9967 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.996732: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> ### Spectrum

> Across 119 [[spectral.n_segments]] segments, the average alpha band power was 3.6058 [[spectral.alpha_band_power_uv2.mean]] uV² and mean relative alpha power was 0.0882 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 119: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 3.60583: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.0882102: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Standard band power mixes oscillations with the aperiodic background, which had an average exponent of 1.919 [[aperiodic.exponent.mean]] and an offset of 1.232 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.91947: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.23235: overall height (log10 power) of the 1/f background. (average over channels)

> Because of this mixing, peak power above the aperiodic fit is the oscillation measure; this yielded an average alpha peak power of 0.834 [[aperiodic.alpha_peak_power.mean]] at a mean frequency of 8.852 [[aperiodic.alpha_peak_freq_hz.mean]] Hz across 18 [[aperiodic.n_channels_with_alpha]] channels.
- `aperiodic.alpha_peak_power.mean` = 0.834204: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)
- `aperiodic.alpha_peak_freq_hz.mean` = 8.85176: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.n_channels_with_alpha` = 18: channels where an alpha peak (7-14 Hz) rises above the 1/f background.

> ### Coupling

> Phase synchrony evaluated across 60 [[connectivity.n_epochs]] epochs produced a mean phase-locking value (PLV) of 0.1242 [[connectivity.plv_mean]] and a mean debiased weighted phase lag index (dwPLI) of 0.00125 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 60: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.124217: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.00124887: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> PLV is inflated by volume conduction while debiased wPLI is not, offering an unbiased estimate of true phase coupling.

> The pair with the strongest dwPLI coupling was Fp1–O1, displaying a dwPLI of 0.0666 [[connectivity.top_pairs.0.dwpli]] and a PLV of 0.1753 [[connectivity.top_pairs.0.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0666323: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.175254: PLV of this pair (inflated by volume conduction).

> ### Events

> No seizure-like events occurred during the session, yielding 0 [[events.n_events]] events, an event rate of 0.0 [[events.rate_per_hour]] per hour, and a cumulative duration of 0.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 0: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 0.0: candidates per hour of recording.
- `events.total_duration_s` = 0.0: total seconds covered by candidates.

## A20

> ### Summary

> This analysis is for research use only.

> The 120.0 [[recording.duration_s]]-second recording contains 19 [[recording.n_channels]] channels sampled at 256.0 [[recording.sfreq_hz]] Hz.
- `recording.duration_s` = 120.0: length of the recording in seconds.
- `recording.n_channels` = 19: number of EEG channels in the file.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> Preprocessing identified 2 [[qc.n_bad]] bad channels and 17 [[qc.n_good]] good channels.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.
- `qc.n_good` = 17: channels kept after quality control.

> Across the data, 2 [[events.n_events]] seizure-like events were detected, totaling 28.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.total_duration_s` = 28.0: total seconds covered by candidates.

> ### Recording

> The recording was performed with a referential montage across 19 [[recording.n_channels]] channels.
- `recording.n_channels` = 19: number of EEG channels in the file.

> It spans a duration of 120.0 [[recording.duration_s]] seconds with a sampling rate of 256.0 [[recording.sfreq_hz]] Hz.
- `recording.duration_s` = 120.0: length of the recording in seconds.
- `recording.sfreq_hz` = 256.0: sampling rate: samples per second (Hz).

> ### Quality

> Data evaluation classified 17 [[qc.n_good]] channels as good and 2 [[qc.n_bad]] channels as bad.
- `qc.n_good` = 17: channels kept after quality control.
- `qc.n_bad` = 2: channels rejected by quality control (flat, noisy or too quiet); they are left out of everything else.

> Specifically, channel T8 was flat for 119.996 [[qc.flat.T8]] seconds, and channel F8 was noisy with a variance ratio of 14.034 [[qc.noisy.F8]].
- `qc.flat.T8` = 119.996: this channel stayed flat (no signal) for this many seconds; more than 5 s marks it bad.
- `qc.noisy.F8` = 14.034: this channel's amplitude spread divided by the median channel's; above 5 marks it noisy (bad). It is a ratio, not microvolts.

> The median line noise ratio decreased from 0.286055 [[qc.line_noise_ratio_before_median]] before filtering to 0.000363584 [[qc.line_noise_ratio_after_median]] after processing.
- `qc.line_noise_ratio_before_median` = 0.286055: 50 Hz mains power divided by total 1-45 Hz power, median over channels, BEFORE cleaning. Smaller after cleaning = noise removed.
- `qc.line_noise_ratio_after_median` = 0.000363584: the same ratio AFTER the 50 Hz notch filter.

> ### Spectrum

> Standard band power mixes oscillations with the aperiodic background (peak power above the aperiodic fit is the oscillation measure).

> Across 89 [[spectral.n_segments]] segments, the mean alpha band power was 25.8701 [[spectral.alpha_band_power_uv2.mean]], and relative alpha power averaged 0.187564 [[spectral.relative_alpha_power.mean]].
- `spectral.n_segments` = 89: number of 2-second windows averaged for the spectrum (windows inside detected events are left out).
- `spectral.alpha_band_power_uv2.mean` = 25.8701: raw power in 8-12 Hz (µV²). It MIXES the alpha rhythm with the 1/f background, so it is NOT a clean oscillation measure. (average over channels)
- `spectral.relative_alpha_power.mean` = 0.187564: 8-12 Hz power as a fraction of all 1-45 Hz power (0 to 1). Also mixes rhythm and background. (average over channels)

> Aperiodic parameterization showed 0 [[aperiodic.n_poor_fits]] poor fits with a mean model R-squared of 0.99071 [[aperiodic.r_squared.mean]].
- `aperiodic.n_poor_fits` = 0: channels whose model fit was unreliable and left out.
- `aperiodic.r_squared.mean` = 0.99071: how well the background-plus-peaks model fits the spectrum (1 = perfect; below 0.8 the channel counts as a poor fit). (average over channels)

> The mean aperiodic exponent was 1.18672 [[aperiodic.exponent.mean]] and the mean offset was 1.49648 [[aperiodic.offset.mean]].
- `aperiodic.exponent.mean` = 1.18672: steepness of the 1/f background slope (typical 1-2). Not an oscillation. (average over channels)
- `aperiodic.offset.mean` = 1.49648: overall height (log10 power) of the 1/f background. (average over channels)

> Periodic alpha peaks were identified in 17 [[aperiodic.n_channels_with_alpha]] channels, yielding a mean peak frequency of 11.1392 [[aperiodic.alpha_peak_freq_hz.mean]] Hz and a mean peak power of 0.702874 [[aperiodic.alpha_peak_power.mean]] above the aperiodic fit.
- `aperiodic.n_channels_with_alpha` = 17: channels where an alpha peak (7-14 Hz) rises above the 1/f background.
- `aperiodic.alpha_peak_freq_hz.mean` = 11.1392: frequency (Hz) of the alpha peak. (average over channels)
- `aperiodic.alpha_peak_power.mean` = 0.702874: height of the alpha peak ABOVE the 1/f background, in log10 units: the CLEAN measure of the alpha oscillation. (average over channels)

> ### Coupling

> Functional connectivity assessed across 46 [[connectivity.n_epochs]] epochs revealed an average phase locking value (PLV) of 0.13865 [[connectivity.plv_mean]] and a mean debiased weighted phase lag index (dwPLI) of 0.000846511 [[connectivity.dwpli_mean]].
- `connectivity.n_epochs` = 46: number of 2-second pieces used to estimate coupling; more epochs = more reliable.
- `connectivity.plv_mean` = 0.13865: phase-locking value averaged over channel pairs. INFLATED by volume conduction: cannot show true connectivity on its own.
- `connectivity.dwpli_mean` = 0.000846511: debiased wPLI averaged over pairs: the trustworthy coupling measure. Near 0 (it can be slightly negative) = no real coupling.

> PLV is inflated by volume conduction while debiased wPLI is not.

> Top synchronized channel pairs included the pairing of C3 and P7 with dwPLI of 0.0725242 [[connectivity.top_pairs.0.dwpli]] and PLV of 0.199025 [[connectivity.top_pairs.0.plv]], and the pairing of F3 and C4 with dwPLI of 0.0700762 [[connectivity.top_pairs.1.dwpli]] and PLV of 0.172742 [[connectivity.top_pairs.1.plv]].
- `connectivity.top_pairs.0.dwpli` = 0.0725242: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.0.plv` = 0.199025: PLV of this pair (inflated by volume conduction).
- `connectivity.top_pairs.1.dwpli` = 0.0700762: debiased wPLI of this pair; pairs are ranked by it. Values below about 0.1 are weak.
- `connectivity.top_pairs.1.plv` = 0.172742: PLV of this pair (inflated by volume conduction).

> ### Events

> A total of 2 [[events.n_events]] seizure-like events occurred, representing an hourly rate of 60.0 [[events.rate_per_hour]] and cumulative duration of 28.0 [[events.total_duration_s]] seconds.
- `events.n_events` = 2: number of seizure-like event CANDIDATES the detector found. Zero means none were found, not that none happened; candidates are not diagnoses.
- `events.rate_per_hour` = 60.0: candidates per hour of recording.
- `events.total_duration_s` = 28.0: total seconds covered by candidates.

> In channel O2, an event began at 10.0 [[events.list.0.onset_s]] seconds and ended at 24.0 [[events.list.0.offset_s]] seconds, lasting 14.0 [[events.list.0.duration_s]] seconds with a dominant frequency of 3.0 [[events.list.0.dominant_freq_hz]] Hz and peak z-score of 1.14323 [[events.list.0.peak_z]].
- `events.list.0.onset_s` = 10.0: when this candidate starts (seconds from the start).
- `events.list.0.offset_s` = 24.0: when this candidate ends (seconds).
- `events.list.0.duration_s` = 14.0: how long this candidate lasts (seconds).
- `events.list.0.dominant_freq_hz` = 3.0: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.0.peak_z` = 1.14323: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.

> In channel P7, another event began at 66.0 [[events.list.1.onset_s]] seconds and ended at 80.0 [[events.list.1.offset_s]] seconds, lasting 14.0 [[events.list.1.duration_s]] seconds with a dominant frequency of 4.0 [[events.list.1.dominant_freq_hz]] Hz and peak z-score of 0.936714 [[events.list.1.peak_z]].
- `events.list.1.onset_s` = 66.0: when this candidate starts (seconds from the start).
- `events.list.1.offset_s` = 80.0: when this candidate ends (seconds).
- `events.list.1.duration_s` = 14.0: how long this candidate lasts (seconds).
- `events.list.1.dominant_freq_hz` = 4.0: main rhythm of the candidate (Hz), read against the background; the detector only keeps 2-7.5 Hz.
- `events.list.1.peak_z` = 0.936714: how far line length rose above the channel's usual level (robust z-score); higher = more pronounced, not more dangerous.
