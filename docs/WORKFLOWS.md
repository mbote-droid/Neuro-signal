# Workflows

Every workflow is one command. All `make` targets run inside the locked
`uv` environment (Python 3.12).

| goal | command | time on 4 cores |
|---|---|---|
| install | `make setup` (`uv sync --frozen`) | about 1 min |
| try it on synthetic data | `make demo` -> `out/demo/report.html` | seconds |
| report on your own file | `uv run neurosignal report path/to/rec.edf --out out/rec` | seconds per hour of data |
| same, with an LLM explanation | `ANTHROPIC_API_KEY=... uv run --extra llm neurosignal report rec.edf --explainer llm` | plus one or two API calls |
| same, with Gemini or a local model | `--explainer gemini --model <name>` (needs `GEMINI_API_KEY`) or `--explainer ollama --model <name>` | seconds (cloud) to minutes (local, CPU) |
| LLM explainer evaluation (H7) | see [LLM_EVALUATION.md](LLM_EVALUATION.md) | about 10 min (Gemini), 1-2 h (local model on CPU) |
| check any explanation | `uv run neurosignal check explanation.md metrics.json` | instant |
| lint, types, tests | `make check` | about 1 min |
| download CHB-MIT subset (checksummed) | `make data` | depends on network, about 650 MB |
| re-tune the detector (synthetic only) | `make tune` | about 15 min |
| full validation campaign + report | `make validate` | about 10 min (plus `make data`) |
| mutation testing of the test suite | `make mutation` | about 5 min |
| theory-versus-measurement checks | `make theory` | about 10 min |
| regenerate the validation report only | `make report` | instant |
| determinism check | `make determinism` | seconds |
| container | `docker build -t neurosignal .` then `docker run --rm -v "$PWD:/data" neurosignal report /data/rec.edf --out /data/out` | |

## Typical session

```bash
make setup
make check                      # everything CI runs
make demo                       # synthetic recording -> out/demo/report.html
make data && make validate      # reproduce every number in VALIDATION_REPORT.md
```

## On the 8 GB laptop

* Use one process per recording; a 1-hour, 32-channel recording peaks at
  the memory reported under P-01.
* `OMP_NUM_THREADS=1` keeps BLAS from oversubscribing cores when the
  campaign runs four worker processes.
* The campaign's `WORKERS = 4` in `validation/campaign.py` can be lowered
  to 2 if memory is tight.
