#!/usr/bin/env bash
# Build paper/preprint.pdf from paper/preprint.md: pandoc to HTML, Chromium to PDF.
# Needs pandoc and a Chromium/Chrome binary (CHROME, default: chromium on PATH).
set -euo pipefail
cd "$(dirname "$0")"
CHROME="${CHROME:-chromium}"
pandoc preprint.md --standalone --embed-resources --css preprint.css \
  --metadata pagetitle="Validation-first EEG pipelines" -o preprint.html
"$CHROME" --headless --disable-gpu --no-sandbox --no-pdf-header-footer \
  --print-to-pdf=preprint.pdf "file://$PWD/preprint.html"
rm preprint.html
echo "wrote paper/preprint.pdf"
