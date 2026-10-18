# Interface control document

Every interface a user, a script or a model touches. Changing one of these
is a breaking change and needs a version bump and a CHANGELOG entry.

## 1. Command line (`neurosignal`)

| command | arguments | exit codes |
|---|---|---|
| `report FILE` | `--out DIR` (default `out`), `--config TOML`, `--explainer template\|llm`, `--max-mb N` (default 2048) | 0 report written and claim check passed; 1 claim check failed; 2 file refused |
| `synth` | `--seed`, `--out FILE.npz`, `--duration`, `--events`, `--snr`, `--flat`, `--noisy`, `--blinks`, `--muscle` | 0; writes `FILE.npz` and `FILE.truth.json` |
| `explain METRICS.json` | `--explainer template\|llm` | 0 passed; 1 failed |
| `check EXPLANATION.md METRICS.json` | | 0 PASS; 1 FAIL (one `CODE<TAB>detail` line per finding) |
| `info FILE` | | 0; 2 refused |

## 2. Input files

| extension | reader | notes |
|---|---|---|
| `.edf` | MNE `read_raw_edf` | EDF and EDF+; physical units honoured |
| `.bdf` | MNE `read_raw_bdf` | |
| `.vhdr` | MNE `read_raw_brainvision` | `.eeg` and `.vmrk` next to it |
| `.npz` | native, `allow_pickle=False` | arrays `data` (µV, channels x samples), `sfreq`, `channels`; optional `ann_onset`, `ann_duration`, `ann_description` |

Refusals (`RefusedFile`): unknown extension; size above the limit; not a
regular file; `.npz` with object arrays or missing keys.

## 3. Configuration (TOML)

Any field of `neurosignal.core.config.PipelineConfig`; lists for ranges.
Unknown keys are an error. Example:

```toml
line_freq_hz = 60.0          # Americas
lowpass_hz = 40.0
alpha_band_hz = [8.0, 13.0]
```

## 4. `metrics.json` (schema v1)

Top-level keys, all always present (`connectivity` may be `null`):

| key | contents |
|---|---|
| `recording` | `subject_id`, `n_channels`, `channels`, `sfreq_hz`, `duration_s`, `montage` (`referential`/`bipolar`) |
| `qc` | `bad_channels`, `n_bad`, `n_good`, `flat`/`noisy`/`low` (channel -> value), `line_noise_reference_band_hz`, `line_noise_ratio_before_median`, `line_noise_ratio_after_median`, `rereferenced` |
| `spectral` | `alpha_band_power_uv2`, `relative_alpha_power` (summaries), `n_segments`, `event_windows_excluded` |
| `aperiodic` | `exponent`, `offset`, `r_squared`, `alpha_peak_freq_hz`, `alpha_peak_power` (summaries), `poor_fit_channels`, `n_poor_fits`, `n_channels_with_alpha` |
| `connectivity` | `n_epochs`, `dwpli_mean`, `wpli_mean`, `plv_mean`, `top_pairs` (list of `a`, `b`, `dwpli`, `plv`) |
| `events` | `n_events`, `total_duration_s`, `rate_per_hour`, `list` (each: `onset_s`, `offset_s`, `duration_s`, `channels`, `n_channels`, `peak_z`, `dominant_freq_hz`) |
| `config` | the full `PipelineConfig` |
| `processing` | one object per stage with every parameter |
| `provenance` | `git` (`commit`, `dirty`), `versions`, `python`, `input_sha256` |

A *summary* is `{mean, sd, min, max, by_channel: {channel: value}}`.
Floats have at most 6 significant digits; non-finite values are `null`;
keys are sorted. No wall-clock time appears (it is in `run.json`).

## 5. Citation keys

A citation is `[[dotted.path]]` into `metrics.json`; list items by index
(`events.list.0.onset_s`, `config.alpha_band_hz.1`). A list of scalars may
also be cited whole (`qc.bad_channels`): every element must then appear in
the text before the citation, or the text must say "none"/"no" when the
list is empty.

## 6. Claim checker result

`CheckResult(findings, n_citations, n_numbers)`; `ok` is true when there
are no findings. Codes: `UNKNOWN_KEY`, `VALUE_MISMATCH`, `MISSING_VALUE`,
`UNCITED_NUMBER`, `UNKNOWN_CHANNEL`, `DIAGNOSTIC`, `NO_DISCLAIMER`.

## 7. LLM request (optional)

`POST /v1/messages` through the Anthropic Python SDK, beta namespace:
model `claude-opus-5-5`, `max_tokens` 8000, `output_config.effort`
`medium`, `betas=["server-side-fallback-2026-07-01"]`,
`fallbacks="default"`. System prompt: `explain/llm.py::SYSTEM_PROMPT`.
User content: the metrics dictionary minus `provenance`, `processing` and
`recording.subject_id`, as sorted JSON. One repair turn, which appends the
model's full reply and the checker's findings. Credentials come from the
SDK's own resolution (environment or `ant auth` profile) and are never
read by this package.

## 8. Validation result files

`results/validation/<experiment>.json`: `experiment`, `provenance`, then
experiment-specific fields; `MANIFEST.sha256` lists every file's hash.
`docs/VALIDATION_REPORT.md` is generated from them.
