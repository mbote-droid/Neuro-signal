# Failure modes and effects analysis

Outputs could be read by someone near a clinical decision (event
candidates in a paediatric recording, for example), so the playbook asks for
an FMEA even though the tool is research use only. ISO 14971 is a design
reference here, not a claim of compliance.

Scales 1-10. S severity, O occurrence, D detection (10 = hard to detect).
RPN = S x O x D. O and D values use measured rates where they exist.

| # | failure mode | effect | cause | S | O | D | RPN | mitigation | evidence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | true rhythmic event missed | reader concludes no event candidates | low-amplitude or focal discharge; ictal rhythm outside the 2-7.5 Hz gate (slow delta < 2 Hz, as in 3 of 7 held-out chb03 seizures, or fast > 7.5 Hz); event shorter than 10 s | 8 | 7 | 8 | 448 | research-use banner; "candidates for expert review, not findings"; per-SNR sensitivity and CHB-MIT misses published | VALIDATION_REPORT (synthetic 0 dB sensitivity; CHB-MIT tables) |
| 2 | false event candidate | wasted review time; alarm fatigue | blink trains, alpha and spindle bursts, peri-ictal rhythmic activity (3.3/h on held-out chb03) | 4 | 6 | 3 | 72 | rhythm gate; false detections per hour reported with upper bound; figure shows the trace | detection and CHB-MIT results |
| 3 | band-power change read as oscillation | wrong scientific conclusion | aperiodic exponent shift | 5 | 6 | 7 | 210 | report gives peak power above aperiodic fit next to band power, with an explicit warning | H1 |
| 4 | spurious connectivity | wrong network conclusion | volume conduction | 5 | 7 | 7 | 245 | dwPLI is the reported measure; PLV shown only as contrast | H3 |
| 5 | LLM states an uncomputed number or a diagnosis | misinformation in the report | model error | 7 | 4 | 2 | 56 | claim checker; fallback to template; failure shown in report | H4 |
| 6 | unit error (V vs µV) | all amplitudes off by 10^6 | reader misuse | 7 | 2 | 2 | 28 | µV by construction; unit test with an mV file | `test_units_are_microvolts` |
| 7 | causal filter in offline analysis | timing shifted by 3.3 s | code change | 6 | 2 | 2 | 24 | zero-phase by design; impulse test; mutation test | `test_zero_phase_does_not_shift_an_impulse`, mutation `causal_instead_of_zero_phase` |
| 8 | bad channel not marked | average reference contaminated | QC thresholds | 5 | 2 | 4 | 40 | flat + amplitude QC; bad channels excluded from CAR | V-04 |
| 9 | wrong reference for bipolar data | meaningless channels | CAR on derivations | 6 | 2 | 2 | 24 | montage detection | `test_bipolar_montage_left_unchanged` |
| 10 | identifiable data in output | privacy breach | header fields | 8 | 1 | 2 | 16 | reader drops identity fields | `test_identifying_header_fields_never_cross_the_boundary` |
| 11 | aperiodic fit fails on a channel | nonsense exponent averaged in | strong event or artifact in spectrum | 4 | 3 | 3 | 36 | event windows excluded; R² and exponent-range check, poor fits listed and excluded | BUILD_JOURNAL ISSUE-004 |

Highest RPN: missed events (1). The tool's design response is to never
present the absence of candidates as a finding, and to publish per-SNR and
real-data miss rates so a reader can judge.
