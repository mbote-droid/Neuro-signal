#!/usr/bin/env bash
# Build the Journal of Neuroscience Methods files from paper/jnm/manuscript.md:
#   manuscript.docx  double-spaced, line-numbered (Word, for submission)
#   manuscript.pdf   review copy (pandoc to HTML, Chromium to PDF)
#   highlights.docx  the highlights as a separate file
# Needs pandoc, python3 and a Chromium/Chrome binary (CHROME, default: chromium).
# Figures come from make_figures.py and are committed under figures/.
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-chromium}"

pandoc manuscript.md --resource-path=. -o manuscript.docx
python3 docx_format.py manuscript.docx

# highlights: a separate editable file with "highlights" in its name
grep '^- ' highlights.md > highlights.tmp.md
pandoc highlights.tmp.md -o highlights.docx
rm highlights.tmp.md

pandoc manuscript.md --standalone --embed-resources --resource-path=. \
  --css ../preprint.css --css manuscript.css \
  --metadata pagetitle="Validation-first EEG pipelines (JNM)" -o manuscript.html
"$CHROME" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf=manuscript.pdf "file://$PWD/manuscript.html"
rm manuscript.html
echo "wrote paper/jnm/manuscript.docx, manuscript.pdf and highlights.docx"
