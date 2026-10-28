# Cover letter (draft)

Dear Editor,

Please consider the manuscript "Validation-first EEG pipelines: how
synthetic benchmarks mislead, and how pre-registration catches it" for
publication as a research article in the Journal of Neuroscience Methods.

The manuscript reports what happened when an open scalp-EEG pipeline was
built and evaluated under a validation-first protocol: hypotheses with
numeric thresholds committed to version control before the code and data
they concern, synthetic ground truth for every method, a held-out subject
of the CHB-MIT database named before download, and mutation testing of
both the test suite and the rule-based checker that verifies language-model
summaries. Four of the first six hypotheses were rejected, and we report
them as such. The paper's methodological contribution is to show, with
dated evidence, how a synthetic benchmark hid four detector failures, how
the estimator rather than only the measure needs pre-registering, and how
the error model behind an automated checker is a researcher degree of
freedom in the same way as a benchmark. A pre-registered evaluation of a
cloud and a small local language model writing under the citation contract
is included; its blinded audit rejected the hypothesis that accepted text
is also right in meaning, and the paper reports why.

We believe the work fits the journal's interest in the validation and
reproducibility of computational methods for neural data. All code,
synthetic generators, result files with provenance and checksums, and the
build journal are openly available (https://doi.org/10.5281/zenodo.23447346).
A preprint is available at https://doi.org/10.5281/zenodo.23448015.

The manuscript is not under consideration elsewhere. The author declares
no competing interests, and the work received no specific funding.

Yours sincerely,

Samuel Ngigi Mbote
Independent Researcher, Nairobi, Kenya
ORCID 0009-0003-2319-8873 · mbotesamuel9@gmail.com
