# Paper

Posted on Zenodo: [10.5281/zenodo.23448015](https://doi.org/10.5281/zenodo.23448015)
(all versions; v1 is 10.5281/zenodo.23448016).

`preprint.md` is the draft of the methods preprint. Numbers come from
`results/validation/*.json` at release v0.1.1 (see
[VALIDATION_REPORT.md](../docs/VALIDATION_REPORT.md)); when a result file
changes, the matching sentence here must change with it.

## Before submission

* Check every reference against the publisher's record.
* Have one person who did not build the tool read Sections 2 and 3.

## Build a PDF

```bash
paper/build_pdf.sh                      # pandoc -> HTML -> Chromium -> paper/preprint.pdf
CHROME=/path/to/chrome paper/build_pdf.sh
pandoc paper/preprint.md -o paper/preprint.tex --standalone   # LaTeX source, if a venue wants it
```

`preprint.pdf` is committed so it can be downloaded and uploaded as is.

## Venues

| venue | format notes |
|---|---|
| arXiv, eess.SP (cross-list q-bio.NC) | LaTeX source or PDF; first submission in a category may need an endorsement |
| bioRxiv (Neuroscience) | PDF; methods papers accepted |
| Journal of Neuroscience Methods | Elsevier format; needs highlights (3-5 bullets of at most 85 characters), a graphical abstract is optional; check the guide for authors for current declarations |
| JOSS (software paper) | a short `paper.md` with its own template; expects evidence of use by others |

## Journal submission

`jnm/` holds the Journal of Neuroscience Methods package: highlights, a
structured abstract, a cover letter and a submission checklist. The H7c
figures in the paper and the package come from
`results/validation/llm_audit.json`.
