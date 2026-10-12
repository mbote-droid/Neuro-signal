# Threat model

Scope: the `neurosignal` CLI run locally on a researcher's machine, reading
files it did not create and optionally sending metrics to the Anthropic
API. STRIDE per asset. Hosting the tool as a service is out of scope
(ADR-011) and would need this model extended first (upload limits, rate
limits, authentication, retention, ephemeral storage).

## Assets

| asset | why it matters |
|---|---|
| A1 recording content and header | health data; identifiable in headers |
| A2 the user's machine | parsers run on untrusted files |
| A3 metrics and report | may inform research decisions; must be correct and traceable |
| A4 API credentials | billing and account access |
| A5 validation evidence | the basis of every claim in the README and report |

## Threats and mitigations

| STRIDE | threat | mitigation | verified by | residual risk |
|---|---|---|---|---|
| Tampering / DoS (A2) | malformed or huge file exhausts memory or triggers a parser bug | size limit before parsing (S-01); extension allowlist, no content sniffing (F-02); mature MNE parsers; finite-value check in every stage | `test_size_limit_checked_before_parsing`, `test_unknown_extension_refused` | a crafted EDF within the size limit could still hit an MNE/NumPy bug; run untrusted files in a container (`Dockerfile`, non-root user) |
| Elevation (A2) | pickle payload in a `.npz` | `np.load(allow_pickle=False)`; object arrays refused (S-05) | `test_npz_with_object_array_refused` | none known |
| Information disclosure (A1) | patient name or dates leak into outputs, logs or figures | reader drops header identity fields; pseudonymous id from the file hash (S-02) | `test_identifying_header_fields_never_cross_the_boundary` | EDF+ annotation text is kept and could contain identifiers |
| Information disclosure (A1) | data sent to a third party | LLM explainer is opt-in and receives metrics only, no signal, no id, no provenance (S-03) | `test_model_sees_metrics_only` | channel names and summary numbers do leave the machine when the LLM is used |
| Information disclosure (A4) | API key written to a report or log | the package never reads the key; the SDK resolves it (S-04) | `test_api_key_never_written` | keys in the user's shell history are outside this tool's control |
| Spoofing / Tampering (A3) | LLM text states numbers, channels or diagnoses that were not computed | citation contract + mechanical claim checker; failed text is replaced by the template and the failure is reported (ADR-009) | H4 campaign; `test_every_mutation_operator_is_caught` | numbers written as words; a cited key that is numerically right but semantically wrong for the sentence |
| Tampering (A3) | untrusted explanation text injects HTML/JS into `report.html` | text is HTML-escaped before the limited Markdown conversion | `test_html_escapes_untrusted_explanation` | none known |
| Tampering (A5) | result files edited by hand | report generated from files; SHA-256 manifest; provenance with git commit and dirty flag (R-04) | `test_manifest_matches_result_files` | a determined author can regenerate everything; the git history is the audit trail |
| Repudiation (A3) | "which settings produced this number?" | every stage's parameters in `metrics.json["processing"]`; full config; versions; input hash (R-02) | `test_provenance_and_processing_history` | none known |
| Prompt injection (A3) | annotation text or channel names crafted to steer the LLM | the LLM never sees annotations; its output is checked regardless of what it was told | checker | a channel name could carry text; it is still subject to the checker |
| Supply chain (A2) | malicious dependency update | `uv.lock` pins versions; Dependabot proposes updates as reviewable PRs; CI runs the full suite on them | CI | upstream compromise of a pinned version |

## Safety statement

Research use only. Not a medical device; not validated for clinical use;
makes no diagnostic statements and is designed to refuse them. IEC 62304
and ISO 14971 were used only as design references for the FMEA.
