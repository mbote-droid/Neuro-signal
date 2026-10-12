# Every workflow is one command. All targets run inside the locked uv environment.
SHELL := /bin/bash
.SHELLFLAGS := -euo pipefail -c
.DEFAULT_GOAL := help

UV ?= uv
RUN := $(UV) run --frozen
export OMP_NUM_THREADS ?= 1
export OPENBLAS_NUM_THREADS ?= 1
export MKL_NUM_THREADS ?= 1

.PHONY: help setup lint typecheck test check demo data tune validate validate-quick report mutation determinism clean

help:  ## list targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

setup:  ## create the locked environment
	$(UV) sync --frozen

lint:  ## ruff lint and format check
	$(RUN) ruff check src tests validation scripts
	$(RUN) ruff format --check src tests validation scripts

typecheck:  ## mypy --strict on the package
	$(RUN) mypy

test:  ## full test suite
	$(RUN) pytest

check: lint typecheck test  ## everything CI runs

demo:  ## synthetic recording with known truth -> out/demo/report.html
	mkdir -p out
	$(RUN) neurosignal synth --seed 42 --out out/demo.npz --duration 300 --events 2
	$(RUN) neurosignal report out/demo.npz --out out/demo
	@echo "open out/demo/report.html; ground truth in out/demo.truth.json"

data:  ## download the CHB-MIT subset, verified against PhysioNet SHA-256 sums
	$(RUN) python scripts/fetch_chbmit.py

tune:  ## choose detector thresholds on synthetic tuning seeds only
	$(RUN) python validation/tune_detector.py

validate:  ## full validation campaign, then regenerate docs/VALIDATION_REPORT.md
	$(RUN) python validation/campaign.py all
	$(RUN) python validation/report.py

validate-quick:  ## smoke run of the synthetic experiments
	for e in aperiodic h1 qc connectivity checker; do $(RUN) python validation/campaign.py $$e --quick; done

report:  ## regenerate the validation report and manifest from result files
	$(RUN) python validation/report.py

mutation:  ## mutation testing of the test suite
	$(RUN) python validation/mutation.py
	$(RUN) python validation/report.py

determinism:  ## same input, two processes, byte-identical metrics.json
	mkdir -p out
	$(RUN) neurosignal synth --seed 5 --out out/det.npz --duration 120 --events 1
	$(RUN) neurosignal report out/det.npz --out out/det1 >/dev/null
	$(RUN) neurosignal report out/det.npz --out out/det2 >/dev/null
	sha256sum out/det1/metrics.json out/det2/metrics.json
	cmp out/det1/metrics.json out/det2/metrics.json

clean:
	rm -rf out dist .pytest_cache .mypy_cache .ruff_cache .hypothesis
