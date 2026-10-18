# Paper

`preprint.md` is the draft of the methods preprint. Numbers come from
`results/validation/*.json` at release v0.1.1 (see
[VALIDATION_REPORT.md](../docs/VALIDATION_REPORT.md)); when a result file
changes, the matching sentence here must change with it.

## Before submission

* Fill the placeholders: affiliation, ORCID, contact, funding, competing
  interests, and the Zenodo DOI (`DOI-PLACEHOLDER`).
* Check every reference against the publisher's record.
* Have one person who did not build the tool read Sections 2 and 3.

## Build a PDF

```bash
pandoc paper/preprint.md -o paper/preprint.pdf --citeproc --pdf-engine=xelatex
pandoc paper/preprint.md -o paper/preprint.tex --standalone   # for arXiv
```

## Venues

| venue | format notes |
|---|---|
| arXiv, eess.SP (cross-list q-bio.NC) | LaTeX source or PDF; first submission in a category may need an endorsement |
| bioRxiv (Neuroscience) | PDF; methods papers accepted |
| Journal of Neuroscience Methods | Elsevier format; needs highlights (3-5 bullets of at most 85 characters), a graphical abstract is optional; check the guide for authors for current declarations |
| JOSS (software paper) | a short `paper.md` with its own template; expects evidence of use by others |
