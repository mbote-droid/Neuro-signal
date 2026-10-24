# Running the LLM explainer evaluation (H7)

H7 ([PROBLEM_STATEMENT.md](PROBLEM_STATEMENT.md) §10) asks how real
language models behave when every number they write must cite a computed
metric. It runs on your own computer, because it needs your Gemini API key
and a local Ollama server. Nothing here costs money.

Commands are for Windows PowerShell, from the repository folder; on Linux
or macOS use `export GEMINI_API_KEY=...` instead of `$env:...`.

## 0. Before anything runs: choose the two models

The registration says the models are chosen before the run and not changed
after seeing output. Pick them now and write them down (or commit them on
a branch, which dates the choice):

* **Cloud:** a model listed under the free tier in Google AI Studio. Use
  the exact name the API expects (for example `gemini-3.8-flash`).
* **Local:** a 3-4 billion parameter instruction-tuned model from
  <https://ollama.com/library>, for example `qwen2.5:3b` or `llama3.2:3b`.
  These need about 2-3 GB of RAM and run on the CPU.

### What the model identifiers mean

* **Parameters** are all the numbers a network learned in training: the
  weights each layer multiplies its inputs by, the biases it adds, and the
  embedding tables. `qwen2.5:3b` has about 3 billion.
* **Quantisation** stores each parameter in fewer bits. At 16 bits, 3
  billion parameters take about 6 GB; Ollama's default 4-bit version takes
  1.9 GB, with a small loss of precision. Running it needs about 2.5-3 GB
  of RAM including the 8,192-token context this evaluation requests.
* **The Ollama ID** (`357c53fb659c` for the H7 model) is the start of a
  SHA-256 fingerprint of the model's manifest: the weight file, prompt
  template and default settings. Its characters carry no meaning on their
  own (hexadecimal, 0-9 and a-f); any change to a single weight gives a
  completely different ID. It identifies the exact model the way a lot
  number identifies a batch, and `validation/llm_eval.py` records it.
* **Cloud model names** such as `gemini-3.8-flash` can be updated by the
  provider; the version the API reports for each reply is recorded instead.

## 1. Get the code and check it

```powershell
git checkout main
git pull
uv sync --frozen
uv run --frozen pytest
```

## 2. Gemini

1. Open <https://aistudio.google.com>, sign in, click **Get API key**, then
   **Create API key**. Copy it.
2. Put it in this PowerShell window only (it is forgotten when the window
   closes; never paste it into a file in the repository):

   ```powershell
   $env:GEMINI_API_KEY = "paste-the-key-here"
   ```

3. Optional smoke test on the demo recording (not one of the H7
   recordings, so it does not count):

   ```powershell
   uv run --frozen neurosignal report out\demo.npz --out out\gemini-demo --explainer gemini --model gemini-3.8-flash
   ```

   The report's "Claim check" line says which model wrote the text, or why
   the template was used instead.

4. The evaluation: 30 recordings and 30-60 calls (a repair round adds a
   call), one call every 13 s to stay inside the free tier's 5 requests per
   minute. On a free tier with 20 requests per day this takes two or three
   days:

   ```powershell
   uv run --frozen python validation/llm_eval.py run --backend gemini --model gemini-3.8-flash
   ```

   When the day's quota is used up, the run stops with a quota message
   (HTTP 429). Run the same command again the next day; it continues where
   it stopped. Every reply is saved before it is checked, so no call is
   ever repeated; only failed calls are retried. Keep other apps that use
   the same Google project from calling Gemini while the run is spread over
   these days, so they do not use up its quota.

## 3. Local model with Ollama

1. Install Ollama from <https://ollama.com/download> and start it (it runs
   in the background; the tray icon shows it).
2. Download the model you chose:

   ```powershell
   ollama pull qwen2.5:3b
   ollama list
   ```

3. The evaluation (on a laptop CPU, roughly 1-3 minutes per recording, so
   1-2 hours; keep the laptop plugged in; it can be stopped and resumed
   the same way as above):

   ```powershell
   uv run --frozen python validation/llm_eval.py run --backend ollama --model qwen2.5:3b
   ```

## 4. Blinded audit (H7c)

```powershell
uv run --frozen python validation/llm_eval.py audit-sheet
```

This writes three files to `results\validation\llm_eval\`:

* `audit_items.md`: up to 20 accepted explanations per model, shuffled
  together with the model hidden; under each, every cited key and its
  value. Open it in VS Code's Markdown preview or any Markdown viewer.
* `audit.csv`: one row per item. Open it in Excel and fill `fails` with
  **1** if the explanation contains at least one statement that is false or
  misleading given the cited values, otherwise **0**. Use `notes` for what
  was wrong.
* `audit_key.json`: which model wrote which item. **Do not open it** until
  `audit.csv` is complete.

What counts as a failure (the errors the checker cannot see):

* a number cited to the wrong metric for the sentence (for example a
  channel count citing a filter setting that happens to have the same
  value);
* a wrong interpretation (for example "PLV shows strong coupling", or
  calling band power an oscillation measure);
* an invented qualitative claim not supported by the metrics (for example
  "activity was mainly frontal" when no metric says so).

Wording, style and length are not failures.

```powershell
uv run --frozen python validation/llm_eval.py audit-score
```

## 5. Report and commit

First the secondary analysis (PROBLEM_STATEMENT §10, amendment): the
corrected checker applied to every saved reply, with no model calls:

```powershell
uv run --frozen python validation/llm_eval.py recheck
uv run --frozen python validation/report.py
git checkout -b results/h7-llm-eval
git add results/validation docs/VALIDATION_REPORT.md
git commit -m "H7: LLM explainer evaluation results (Gemini and local Ollama model)"
git push -u origin results/h7-llm-eval
```

Then open the pull request on GitHub. The result files hold the model
names and versions as reported by each API, every reply, and the audit
verdicts. They contain no API key.

## Troubleshooting

* **A new VS Code terminal runs `Set-ExecutionPolicy ... Activate.ps1` by
  itself.** That is VS Code's Python extension activating the project's
  `.venv` (setting `python.terminal.activateEnvironment`). The policy
  change applies to that window only. Harmless; untick the setting to stop
  it.
* **"model 'gemini-3.8-flash' not found" from localhost:11434.** The
  Gemini model name was given to the Ollama backend. Use `--backend gemini`
  with the Gemini name and `--backend ollama` with `qwen2.5:3b`. A resumed
  run with a different model than its saved replies is refused.
* **`ollama --list` fails.** It is a command, not a flag: `ollama list`.
* **"cannot reach http://localhost:11434".** Ollama is not running: start
  it from the Start menu.
* **The Gemini run stops with HTTP 429.** The day's free quota is used up;
  run the same command the next day.
* **Two runs at once.** Gemini and Ollama can run in two terminals at the
  same time; they write separate files. Set `GEMINI_API_KEY` in the Gemini
  terminal. Running Ollama inside WSL is not faster: the Windows Ollama
  server already does the work.
* **`ollama ps`** shows whether the model runs on the CPU or a GPU, and
  that no other model is loaded.
