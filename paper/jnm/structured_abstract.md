# Structured abstract (Journal of Neuroscience Methods format)

Journal of Neuroscience Methods asks research articles for an abstract under
the headings below; check the current word limit in the Guide for Authors.
H7C-PENDING marks the audit result.

**Background.** EEG analysis pipelines are usually evaluated on benchmarks
their authors design, with outcome measures chosen after the results, and
language models increasingly summarise their output without any check on
the numbers they state.

**New method.** An open, deterministic scalp-EEG pipeline (quality control,
zero-phase filtering, aperiodic and periodic spectral parameterisation,
debiased wPLI, an unsupervised rhythmic-event detector) was built under a
validation-first protocol: seven hypotheses with numeric thresholds were
committed before the code or data they concern, every method was tested
against synthetic ground truth, and plain-language summaries must cite a
computed metric for every number, which a rule-based checker verifies.

**Results.** Four of the first six hypotheses were rejected. A synthetic
benchmark on which the detector passed hid four failure modes, including
the 1/f confound the project set out to avoid; on a held-out CHB-MIT
subject the frozen detector found 4 of 7 seizures at 3.3 false detections
per hour. A cloud language model met the citation contract on 30 of 30
recordings and a small local model on 0 of 30, with every faulty text
blocked. The checker as first released missed 709 of 3334 mutated
explanations that an outside report and a bug hunt supplied; the corrected
checker caught all. H7C-PENDING.

**Comparison with existing methods.** Patient-specific seizure detectors
reach far higher sensitivity; the contribution is a protocol and an
evidence trail that make such claims checkable, not a better detector.

**Conclusions.** Benchmarks and error models are researcher degrees of
freedom; pre-registration and mutation testing make their failures visible.
