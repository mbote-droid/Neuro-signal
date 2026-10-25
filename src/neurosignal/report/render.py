"""Write metrics.json, report.md and a self-contained report.html (F-13).

Explanation text may come from an LLM and is treated as untrusted: it is
HTML-escaped before the few Markdown constructs we emit are converted, and
citations become chips showing the cited value.
"""

from __future__ import annotations

import base64
import html
import json
import re
from pathlib import Path
from typing import Any

from neurosignal.explain.checker import CITATION, CheckResult
from neurosignal.pipeline import Analysis, flatten
from neurosignal.report import figures


def write_metrics(metrics: dict[str, Any], path: Path) -> None:
    path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def make_figures(an: Analysis, outdir: Path) -> dict[str, Path]:
    figdir = outdir / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    out = {
        "spectrum": figures.spectrum_figure(an, figdir / "spectrum.png"),
        "channels": figures.channel_figure(an, figdir / "channels.png"),
        "events": figures.events_figure(an, figdir / "events.png"),
    }
    conn = figures.connectivity_figure(an, figdir / "connectivity.png")
    if conn is not None:
        out["connectivity"] = conn
    return out


def _md_to_html(text: str, metrics: dict[str, Any]) -> str:
    flat = flatten(metrics)

    def chip(m: re.Match[str]) -> str:
        key = m.group(1)
        val = flat.get(key, "unknown key")
        tip = html.escape(f"{key} = {val}", quote=True)
        return f'<span class="cite" title="{tip}">{html.escape(key)}</span>'

    out: list[str] = []
    in_list = False
    for raw in html.escape(text, quote=False).splitlines():
        line = CITATION.sub(chip, raw)
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        if line.startswith(("- ", "* ")):  # LLMs use either bullet
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{line[2:]}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if heading := re.match(r"(#{1,6})\s+(.*)", line):
            # explanation headings sit under the page's h2; any '#' depth (models
            # write '##' as often as the template's '###') becomes h3, deeper h4
            level = 3 if len(heading.group(1)) <= 3 else 4
            out.append(f"<h{level}>{heading.group(2)}</h{level}>")
        elif line.strip():
            out.append(f"<p>{line}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


def _img(path: Path, alt: str) -> str:
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f'<figure><img alt="{html.escape(alt)}" src="data:image/png;base64,{data}"></figure>'


def _check_html(result: CheckResult, source: str) -> str:
    if result.ok:
        return (
            f'<p class="ok">Claim check passed: {result.n_citations} citations, '
            f"{result.n_numbers} numbers, every number traced to a computed metric "
            f"({html.escape(source)}).</p>"
        )
    items = "".join(
        f"<li><code>{html.escape(f.code)}</code> {html.escape(f.detail)}</li>"
        for f in result.findings
    )
    return (
        f'<div class="bad"><p>Claim check failed ({html.escape(source)}):</p><ul>{items}</ul></div>'
    )


CSS = """
:root{--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--chip:#e8f0fb;--ok:#1d6b3a;--bad:#a12622;--warn:#fff4d6}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#3a3936;--chip:#1f3550;--ok:#7fd49c;--bad:#f19a98;--warn:#3b3220}}
:root[data-theme="dark"]{--bg:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--line:#3a3936;--chip:#1f3550;--ok:#7fd49c;--bad:#f19a98;--warn:#3b3220}
body{background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif;margin:0;padding:0 16px}
main{max-width:860px;margin:24px auto}
h1{font-size:1.5rem;margin:.2em 0} h2{font-size:1.15rem;margin-top:2em;border-bottom:1px solid var(--line)}
h3{font-size:1rem;margin-bottom:.2em}
.banner{background:var(--warn);border:1px solid var(--line);padding:8px 12px;border-radius:6px}
.cite{background:var(--chip);border-radius:4px;padding:0 4px;font:11px ui-monospace,monospace;color:var(--ink2);cursor:help}
.ok{color:var(--ok)} .bad{color:var(--bad)}
figure{margin:12px 0} img{max-width:100%;height:auto;background:#fff;border-radius:4px}
table{border-collapse:collapse;width:100%;font-size:13px} td,th{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left}
code{font:12px ui-monospace,monospace} .muted{color:var(--ink2);font-size:13px}
"""


def _processing_table(metrics: dict[str, Any]) -> str:
    rows = []
    for step in metrics.get("processing", []):
        params = {k: v for k, v in step.items() if k != "stage"}
        rows.append(
            f"<tr><td>{html.escape(str(step.get('stage')))}</td>"
            f"<td><code>{html.escape(json.dumps(params, sort_keys=True))}</code></td></tr>"
        )
    return "<table><tr><th>stage</th><th>parameters</th></tr>" + "".join(rows) + "</table>"


def write_html(
    metrics: dict[str, Any],
    explanation: str,
    result: CheckResult,
    source: str,
    figs: dict[str, Path],
    path: Path,
) -> None:
    prov = metrics["provenance"]
    titles = {
        "spectrum": "Power spectrum with aperiodic fit",
        "channels": "Per-channel spectral parameters",
        "connectivity": "Alpha-band coupling: debiased wPLI vs PLV",
        "events": "Event detector trace",
    }
    figs_html = "".join(f"<h3>{titles[k]}</h3>{_img(p, titles[k])}" for k, p in figs.items())
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>EEG Signal Report</title><style>{CSS}</style></head>
<body><main>
<p class="banner"><strong>Research use only.</strong> Not a medical device. No clinical statements.</p>
<h1>EEG signal report</h1>
<p class="muted">Recording <code>{html.escape(str(metrics["recording"]["subject_id"]))}</code> ·
input SHA-256 <code>{html.escape(str(prov.get("input_sha256", ""))[:16])}…</code> ·
neurosignal {html.escape(str(prov["versions"]["neurosignal"]))} ·
commit <code>{html.escape(str(prov["git"]["commit"] or "unknown")[:10])}</code></p>
<h2>Explanation</h2>
{_check_html(result, source)}
{_md_to_html(explanation, metrics)}
<h2>Figures</h2>
{figs_html}
<h2>Processing</h2>
<p class="muted">Every parameter that touched the data, in order.</p>
{_processing_table(metrics)}
<p class="muted">All values: <code>metrics.json</code>. Hover a citation chip to see the value it cites.</p>
</main></body></html>
"""
    path.write_text(doc, encoding="utf-8")


def write_markdown(
    metrics: dict[str, Any], explanation: str, result: CheckResult, source: str, path: Path
) -> None:
    status = "passed" if result.ok else "FAILED: " + ", ".join(sorted(result.codes()))
    lines = [
        "# EEG signal report",
        "",
        "> **Research use only.** Not a medical device. No clinical statements.",
        "",
        f"Claim check {status} ({result.n_citations} citations; "
        f"explanation source: {html.escape(source, quote=False)}).",
        "",
        # model text and channel names are untrusted: Markdown viewers render raw
        # HTML, so it is escaped here (explanation.md keeps the checked text as is)
        html.escape(explanation, quote=False),
        "## Figures",
        "",
        "![spectrum](figures/spectrum.png)",
        "![channels](figures/channels.png)",
        "![connectivity](figures/connectivity.png)" if metrics.get("connectivity") else "",
        "![events](figures/events.png)",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
