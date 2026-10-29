# Journal of Neuroscience Methods: submission checklist

Check each item against the journal's current Guide for Authors on the day
of submission; requirements change.

| item | status | file or note |
|---|---|---|
| H7c audit done and filled into the paper | done | `results/validation/llm_audit.json`: 3/20, rejected |
| Preprint v2 posted (Zenodo new version of 10.5281/zenodo.23448015) | done | 10.5281/zenodo.23750975 |
| Software release containing H7 and the bug hunt, cited in the paper | done | v0.1.2, 10.5281/zenodo.23716723 |
| Manuscript in the journal's format (title page, structured abstract, sections, references in journal style) | done | `manuscript.docx` (double-spaced, line-numbered) and `manuscript.pdf`, built from `manuscript.md` by `build.sh`; check the reference details (pages, DOIs) against the originals |
| Highlights (3-5 bullets, max 85 characters each) | drafted | `highlights.md` |
| Structured abstract (Background, New method, Results, Comparison with existing methods, Conclusions) | done | 248 words; `structured_abstract.md` |
| Cover letter | drafted | `cover_letter.md` |
| Graphical abstract | optional | `figures/fig1_workflow` can serve |
| Figures as separate files at the required resolution | done | `figures/`: vector PDF and 600 dpi TIFF, made by `make_figures.py` from the result files |
| Data availability statement | in the paper | Zenodo DOIs and PhysioNet |
| Funding and competing-interest declarations | in the paper | |
| Author's ORCID | in the paper | |
| Acknowledgement of the reporter of issue #21 | pending | ask how they wish to be named |
| Declarations requested by the submission form | at submission | answer the form's questions as they appear |
| Suggested reviewers (if requested) | to do | researchers in EEG methods and reproducibility, no conflicts |
