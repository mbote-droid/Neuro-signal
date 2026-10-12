# Diagrams

Mermaid diagrams render on GitHub.

## 1. Signal chain and closed loop (system framing)

```mermaid
flowchart LR
    brain((brain)) --> elec[electrodes] --> amp[amplifier + ADC] --> file[(EDF / BDF / BrainVision)]
    file --> reader[reader<br/>size + extension check<br/>µV, no identity fields]
    reader --> qc1[flat-channel QC<br/>raw data]
    qc1 --> filt[notch 50 Hz + 0.5-45 Hz<br/>zero-phase FIR]
    filt --> qc2[amplitude QC<br/>MAD ratios]
    qc2 --> car[common average<br/>referential only]
    car --> det[event detector<br/>1-20 Hz line length<br/>+ rhythm gate]
    car --> spec[Welch spectra<br/>outside events]
    det -. exclude windows .-> spec
    spec --> ap[aperiodic + peaks]
    car --> conn[dwPLI / PLV<br/>outside events]
    det -. exclude windows .-> conn
    ap & conn & det --> metrics[(metrics.json)]
    metrics --> expl[explainer<br/>template or LLM]
    expl --> chk{claim checker}
    metrics --> chk
    chk --> report[report.html / report.md]
    report --> reader2((researcher))
    reader2 -. decides what to look at .-> file
```

The "sensor" whose errors propagate is the metrics layer; the claim checker
is the second sensor, validated by mutation testing.

## 2. Components (C4 level 2)

```mermaid
flowchart TB
    subgraph package[neurosignal package]
        core[core<br/>Recording, Stage, config,<br/>provenance, stats]
        io[io<br/>readers, refusals]
        pre[preprocessing<br/>QC, filters, CAR]
        feat[features<br/>spectra, aperiodic, coupling]
        detn[detection<br/>detector, scoring]
        pipe[pipeline]
        expl[explain<br/>template, LLM, checker]
        rep[report<br/>figures, HTML, Markdown]
        cli[cli]
        syn[synth<br/>ground truth]
    end
    val[validation/<br/>campaign, tuning, mutants,<br/>mutation testing, report]
    api[(Anthropic API<br/>optional)]
    cli --> rep --> expl --> pipe --> detn --> feat --> pre --> io --> core
    syn --> core
    expl -. metrics only .-> api
    val --> package
```

## 3. Data and security boundaries

```mermaid
flowchart LR
    subgraph untrusted[untrusted input]
        f[(recording file)]
        llmtext[LLM text]
    end
    subgraph trusted[validated core]
        r[reader] --> p[pipeline] --> m[(metrics.json)]
    end
    subgraph hidden[validation only]
        gt[(ground truth)]
    end
    f -->|size + extension check first| r
    m -->|numbers only, no ids, no signal| llm[[LLM]]
    llm --> llmtext -->|checked against metrics| chk{checker}
    m --> chk
    gt -. never visible to methods .-> score[scoring]
    m --> score
```

## 4. Report sequence

```mermaid
sequenceDiagram
    actor U as user
    participant C as CLI
    participant R as reader
    participant P as pipeline
    participant E as explainer
    participant K as checker
    participant H as renderer
    U->>C: neurosignal report rec.edf
    C->>R: read(path, max_bytes)
    R-->>C: Recording (µV, pseudonymous id)
    C->>P: analyse(rec, config)
    P-->>C: Analysis -> metrics.json
    C->>E: explain(metrics)
    E-->>C: text with [[citations]]
    C->>K: check(text, metrics)
    K-->>C: findings (empty = pass)
    C->>H: write report.html, report.md, figures
    H-->>U: report + claim-check status
```

## 5. LLM explanation states

```mermaid
stateDiagram-v2
    [*] --> Draft: metrics sent
    Draft --> Accepted: checker passes
    Draft --> Repair: findings
    Repair --> Accepted: checker passes
    Repair --> Fallback: findings again
    Fallback --> Accepted: deterministic template
    Accepted --> [*]
```

## 6. Validation campaign

```mermaid
flowchart LR
    tune[tune_detector.py<br/>seeds 0-59] --> cfg[(PipelineConfig<br/>thresholds)]
    cfg --> h2[detection<br/>seeds 1000-1199]
    cfg --> h5[CHB-MIT chb01<br/>H5, then dev set]
    cfg --> h6[CHB-MIT chb03<br/>H6, held out]
    ap[aperiodic<br/>V-01..V-03] & h1[H1] & qc[QC V-04] & h3[H3] & h4[H4 checker] & res[P-01] & h2 & h5 & h6 --> rf[(results/validation/*.json)]
    mut[mutation.py<br/>code mutants] --> rf
    rf --> rep[report.py] --> vr[VALIDATION_REPORT.md<br/>+ MANIFEST.sha256]
```
