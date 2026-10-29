# Structured abstract

The same text opens `manuscript.md` (249 words without the headings; the
journal's limit is 250).

**Background:** EEG analysis pipelines are usually evaluated on benchmarks
their authors design, with outcome measures chosen after the results, and
language models summarise such output with no check on the numbers they
state.

**New method:** An open, deterministic scalp-EEG pipeline (quality control,
zero-phase filtering, aperiodic and periodic spectral parameterisation,
debiased weighted phase-lag index, an unsupervised rhythmic-event detector)
was built under a
validation-first protocol: hypotheses with numeric thresholds were committed
before the code or data they concern, methods were tested against synthetic
ground truth, and every number in a plain-language summary must cite a
computed metric, which a rule-based checker verifies.

**Results:** Four of six initial hypotheses were rejected. A synthetic
benchmark on which the detector passed hid four failure modes, including the
1/f confound the project set out to avoid; on a held-out subject of the
public CHB-MIT database the frozen detector found 4 of 7 seizures at 3.3 false detections per hour. A
cloud language model met the citation contract on 30 of 30 recordings and a
small local model on 0 of 30, with all faulty text blocked. The checker as
first released missed 709 of 3334 mutated explanations; the corrected
checker caught all. A blinded audit found 3 of 20 accepted explanations
misleading (limit 2): correct numbers attached to the wrong concept.

**Comparison with existing methods:** Patient-specific seizure detectors
reach far higher sensitivity; the contribution is a protocol that makes such
claims checkable, not a better detector.

**Conclusions:** Benchmarks and error models are researcher degrees of
freedom; pre-registration and mutation testing make their failures visible.
