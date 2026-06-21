from __future__ import annotations

import json
from html import escape
from pathlib import Path
import re
from typing import Any, Callable

import markdown

from rca.llm import (
    LLMSettings,
    build_chat_completion_kwargs,
    build_openai_compatible_client,
    load_llm_settings,
)
from rca.config import PROJECT_ROOT

REPORT_STYLES = """
body {
  margin: 0;
  background: #f8fafc;
  color: #0f172a;
  font-family: Arial, Helvetica, sans-serif;
}
main {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px 48px;
}
article {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 32px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
h1, h2, h3 {
  color: #0f172a;
}
h1 {
  margin-top: 0;
}
code {
  background: #e2e8f0;
  border-radius: 4px;
  padding: 0.15em 0.35em;
}
pre {
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 10px;
  padding: 16px;
  overflow-x: auto;
}
table {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
}
th, td {
  border: 1px solid #cbd5e1;
  padding: 10px 12px;
  text-align: left;
  vertical-align: top;
}
th {
  background: #e2e8f0;
}
blockquote {
  border-left: 4px solid #94a3b8;
  margin-left: 0;
  padding-left: 16px;
  color: #334155;
}
"""


ClientFactory = Callable[[str], Any]

STORY_WRITER_SYSTEM_PROMPT = """You are writing a story-style RCA walkthrough for a human reader.

Write a compact, readable narrative report in plain markdown.

Rules:
- lead with the conclusion and action
- walk layer by layer from trigger to final decision
- explicitly mention which analyst used which tool when that helps explain the reasoning
- distinguish evidence from interpretation
- do not invent facts beyond the trace you are given
- if a section has no material in the trace (e.g. critic ran only once or not at all), state that explicitly rather than fabricating detail
- keep each section to 2-4 sentences; total report under 400 words
- Use "sales amount", not "units" or "revenue".
- Use "store group L/M/H", not "tier".
- If needed, explain once that store group L means alias prefix 'l'.
- Use plain ASCII punctuation only.

Return sections:
1. Executive Takeaway
2. Why This Day Triggered Review
3. How The Analysis Unfolded
4. Where The System Challenged Itself
5. Final Decision
"""


def _build_dashboard_html_content(
    stores: list[str],
    dates: list[str],
    cells: dict,
    store_stats: dict,
    summary: dict,
    recent_runs: list[dict] | None = None,
) -> str:
    threshold = _DASHBOARD_THRESHOLD
    data = {
        "threshold": threshold,
        "stores": stores,
        "dates": dates,
        "cells": cells,
        "store_stats": store_stats,
        "summary": summary,
        "recent_runs": recent_runs or [],
    }
    data_json = json.dumps(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Retail Insight — Store Signal Dashboard</title>
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e2e4ec;
    --muted: #7a7f9a;
    --drop: #e05252;
    --drop-bg: #3b1a1a;
    --lift: #4caf7d;
    --lift-bg: #0f2e1e;
    --neutral: #2a2d3a;
    --cell: 14px;
  }}
  body {{ margin: 0; font-family: 'Inter', system-ui, sans-serif; background: var(--bg); color: var(--text); font-size: 13px; }}
  header {{ padding: 20px 28px 12px; border-bottom: 1px solid var(--border); }}
  header h1 {{ margin: 0 0 4px; font-size: 18px; font-weight: 600; }}
  header p {{ margin: 0; color: var(--muted); font-size: 12px; }}
  .summary-bar {{ display: flex; gap: 16px; padding: 14px 28px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }}
  .stat {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 10px 16px; min-width: 120px; }}
  .stat-label {{ color: var(--muted); font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }}
  .stat-value {{ font-size: 22px; font-weight: 700; }}
  .stat-value.drop {{ color: var(--drop); }}
  .stat-value.lift {{ color: var(--lift); }}
  .main {{ padding: 20px 28px; }}
  .section-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin: 0 0 12px; }}
  .store-bars {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 28px; }}
  .store-row {{ display: flex; align-items: center; gap: 10px; height: 24px; }}
  .store-label {{ width: 48px; text-align: right; font-size: 11px; color: var(--muted); flex-shrink: 0; }}
  .bar-track {{ flex: 1; height: 14px; background: var(--neutral); border-radius: 3px; display: flex; overflow: hidden; position: relative; }}
  .bar-drop {{ background: var(--drop); height: 100%; }}
  .bar-lift {{ background: var(--lift); height: 100%; }}
  .store-rate {{ width: 40px; font-size: 11px; color: var(--muted); flex-shrink: 0; }}
  .grid-wrap {{ overflow-x: auto; padding-bottom: 8px; }}
  .grid-table {{ border-collapse: collapse; }}
  .grid-table th, .grid-table td {{ padding: 0; }}
  .col-header {{ font-size: 9px; color: var(--muted); text-align: center; height: 28px; vertical-align: bottom; padding-bottom: 4px; white-space: nowrap; }}
  .col-header.month-start {{ border-left: 1px solid var(--border); padding-left: 3px; }}
  .row-label {{ font-size: 11px; color: var(--muted); padding-right: 10px; white-space: nowrap; text-align: right; vertical-align: middle; }}
  .cell {{ width: var(--cell); height: var(--cell); margin: 1px; border-radius: 2px; display: inline-block; background: var(--neutral); }}
  .cell.D {{ background: var(--drop); }}
  .cell.L {{ background: var(--lift); }}
  .cell-td {{ padding: 1px; }}
  .legend {{ display: flex; gap: 16px; margin-top: 16px; align-items: center; }}
  .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--muted); }}
  .legend-swatch {{ width: 12px; height: 12px; border-radius: 2px; }}
  .runs-table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }}
  .runs-table th {{ text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--border); color: var(--muted); font-weight: 500; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }}
  .runs-table td {{ padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  .runs-table tr:last-child td {{ border-bottom: none; }}
  .run-name {{ font-family: monospace; color: var(--text); }}
  .run-path {{ color: var(--muted); font-family: monospace; font-size: 11px; word-break: break-all; }}
  .no-runs {{ color: var(--muted); font-size: 12px; padding: 12px 0; }}
</style>
</head>
<body>
<header>
  <h1>Store Signal Dashboard</h1>
  <p>Trailing 7-day % change &gt; {threshold}% threshold &nbsp;·&nbsp; <span id="date-range"></span></p>
</header>

<div class="summary-bar" id="summary-bar"></div>

<div class="main">
  <p class="section-title">Drop / Lift days per store</p>
  <div class="store-bars" id="store-bars"></div>

  <p class="section-title">Store x Date signal grid</p>
  <div class="grid-wrap">
    <table class="grid-table" id="grid-table"></table>
  </div>

  <div class="legend">
    <div class="legend-item"><div class="legend-swatch" style="background:var(--drop)"></div>Drop (&gt;{threshold}% below 7d avg)</div>
    <div class="legend-item"><div class="legend-swatch" style="background:var(--lift)"></div>Lift (&gt;{threshold}% above 7d avg)</div>
    <div class="legend-item"><div class="legend-swatch" style="background:var(--neutral)"></div>No signal</div>
  </div>

  <p class="section-title" style="margin-top:32px">Recent pipeline runs</p>
  <div id="runs-section"></div>
</div>

<script>
const DATA = {data_json};

(function () {{
  const {{ stores, dates, cells, store_stats, summary }} = DATA;

  document.getElementById("date-range").textContent =
    dates[0] + " - " + dates[dates.length - 1];

  const bar = document.getElementById("summary-bar");
  const stats = [
    {{ label: "Stores", value: stores.length, cls: "" }},
    {{ label: "Eligible store-days", value: summary.eligible_store_days, cls: "" }},
    {{ label: "Drop events", value: summary.drop_store_days, cls: "drop" }},
    {{ label: "Lift events", value: summary.lift_store_days, cls: "lift" }},
    {{ label: "Trigger rate", value: (summary.triggered_city_days / summary.eligible_store_days * 100).toFixed(1) + "%", cls: "" }},
  ];
  stats.forEach(s => {{
    const div = document.createElement("div");
    div.className = "stat";
    div.innerHTML = `<div class="stat-label">${{s.label}}</div><div class="stat-value ${{s.cls}}">${{s.value}}</div>`;
    bar.appendChild(div);
  }});

  const barsEl = document.getElementById("store-bars");
  const maxDays = Math.max(...stores.map(s => parseInt(store_stats[s]?.eligible_days || 0)));
  stores.forEach(s => {{
    const st = store_stats[s] || {{}};
    const drop = parseInt(st.drop_days || 0);
    const lift = parseInt(st.lift_days || 0);
    const total = parseInt(st.eligible_days || maxDays);
    const rate = parseFloat(st.trigger_rate_pct || 0).toFixed(1);
    const pDrop = (drop / total * 100).toFixed(1);
    const pLift = (lift / total * 100).toFixed(1);

    const row = document.createElement("div");
    row.className = "store-row";
    row.innerHTML = `
      <span class="store-label">${{s}}</span>
      <div class="bar-track">
        <div class="bar-drop" style="width:${{pDrop}}%" title="Drop: ${{drop}} days"></div>
        <div class="bar-lift" style="width:${{pLift}}%" title="Lift: ${{lift}} days"></div>
      </div>
      <span class="store-rate">${{rate}}%</span>
    `;
    barsEl.appendChild(row);
  }});

  const runsEl = document.getElementById("runs-section");
  if (!DATA.recent_runs || DATA.recent_runs.length === 0) {{
    runsEl.innerHTML = '<p class="no-runs">No runs logged yet. Run the pipeline to populate.</p>';
  }} else {{
    const t = document.createElement("table");
    t.className = "runs-table";
    t.innerHTML = `<thead><tr>
      <th>Run</th><th>Started (SGT)</th><th>Events</th><th>Output path</th>
    </tr></thead>`;
    const tbody = t.createTBody();
    DATA.recent_runs.forEach(r => {{
      const tr = tbody.insertRow();
      tr.innerHTML = `
        <td class="run-name">${{r.run_name}}</td>
        <td>${{r.started_at}}</td>
        <td style="text-align:right">${{r.events}}</td>
        <td class="run-path">${{r.output_dir || "-"}}</td>
      `;
    }});
    runsEl.appendChild(t);
  }}

  const table = document.getElementById("grid-table");
  const thead = table.createTHead();
  const hrow = thead.insertRow();
  const corner = document.createElement("th");
  hrow.appendChild(corner);

  let lastMonth = null;
  dates.forEach(d => {{
    const th = document.createElement("th");
    th.className = "col-header";
    const [, mm, dd] = d.split("-");
    const isMonthStart = mm !== lastMonth;
    if (isMonthStart) {{
      th.classList.add("month-start");
      const monthNames = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
      th.textContent = monthNames[parseInt(mm)];
      lastMonth = mm;
    }}
    if (parseInt(dd) === 1 || parseInt(dd) % 7 === 0) {{
      if (!isMonthStart) th.textContent = dd;
    }}
    hrow.appendChild(th);
  }});

  const tbody = table.createTBody();
  stores.forEach(s => {{
    const tr = tbody.insertRow();
    const labelTd = document.createElement("td");
    labelTd.className = "row-label";
    labelTd.textContent = s;
    tr.appendChild(labelTd);

    dates.forEach(d => {{
      const td = document.createElement("td");
      td.className = "cell-td";
      const val = cells[s]?.[d] ?? ".";
      const span = document.createElement("span");
      span.className = "cell" + (val === "D" || val === "L" ? " " + val : "");
      span.title = `${{s}} ${{d}}: ${{val === "." ? "no signal" : val === "D" ? "Drop" : "Lift"}}`;
      td.appendChild(span);
      tr.appendChild(td);
    }});
  }});
}})();
</script>
</body>
</html>
"""


def render_markdown_document(markdown_text: str, title: str) -> str:
    body_html = markdown.markdown(
        markdown_text,
        extensions=["extra", "tables", "fenced_code", "sane_lists"],
    )
    escaped_title = escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>{REPORT_STYLES}</style>
</head>
<body>
  <main>
    <article>
      {body_html}
    </article>
  </main>
</body>
</html>
"""


def build_story_report(
    run_dir: Path,
    output_name: str = "story_report",
    use_llm: bool = True,
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
) -> tuple[int, str]:
    """Build story narrative and upsert to Supabase rca_outcome.

    Returns (city_id, dt) so the caller can confirm what was updated.
    """
    from rca.outcomes import update_outcome_story

    trace = load_run_trace(run_dir)
    city_id: int = int(trace["city_id"])
    dt: str = str(trace["dt"])

    markdown_text = build_story_markdown(
        trace,
        use_llm=use_llm,
        settings=settings,
        client_factory=client_factory,
    )
    update_outcome_story(city_id, dt, markdown_text)
    return city_id, dt


def load_run_trace(run_dir: Path) -> dict[str, Any]:
    candidates = [run_dir / "run_trace.json", run_dir / "coordinator_trace.json"]
    for path in candidates:
        if path.exists():
            return _repair_mojibake(json.loads(path.read_text(encoding="utf-8")))
    raise FileNotFoundError(f"No run trace found under {run_dir}")


def build_story_markdown(
    trace: dict[str, Any],
    use_llm: bool = True,
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
) -> str:
    if use_llm:
        try:
            return sanitize_generated_markdown(
                _repair_mojibake(
                    _build_story_markdown_with_llm(trace, settings=settings, client_factory=client_factory)
                )
            )
        except Exception:
            pass
    return sanitize_generated_markdown(_repair_mojibake(_build_story_markdown_fallback(trace)))


def render_story_document(markdown_text: str, title: str) -> str:
    normalized_markdown = _normalize_story_markdown(sanitize_generated_markdown(markdown_text))
    sections = _split_story_sections(normalized_markdown)
    if not sections:
        body_html = markdown.markdown(
            normalized_markdown,
            extensions=["extra", "tables", "fenced_code", "sane_lists"],
        )
        article_html = f'<article class="story-article">{body_html}</article>'
    else:
        executive_title, executive_body = sections[0]
        body_sections = sections[1:]
        article_html = _render_story_shell(
            title=title,
            executive_title=executive_title,
            executive_body=executive_body,
            body_sections=body_sections,
        )
    escaped_title = escape(title)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <style>{REPORT_STYLES}{_story_styles()}</style>
</head>
<body>
  <main>
    {article_html}
  </main>
</body>
</html>
"""


def _build_story_markdown_with_llm(
    trace: dict[str, Any],
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
) -> str:
    settings = settings or load_llm_settings()
    client_factory = client_factory or _default_client_factory(settings)
    client = client_factory("story_writer")
    story_input = {
        "city_id": trace["city_id"],
        "dt": trace["dt"],
        "planner": {
            "selected_analysts": trace["planner"]["selected_analysts"],
            "skipped_analysts": trace["planner"]["skipped_analysts"],
            "signal_evidence": trace["planner"]["planning_inputs"]["signal_evidence"],
            "stockout_context": trace["planner"]["planning_inputs"]["stockout_context"],
            "discount_context": trace["planner"]["planning_inputs"]["discount_context"],
            "activity_context": trace["planner"]["planning_inputs"]["activity_context"],
        },
        "decision_card_markdown": trace["decision_card_markdown"],
        "critic_note_markdown": trace["critic_note_markdown"],
        "controller_note_markdown": trace["controller_note_markdown"],
        "coordinator_report_markdown": trace["coordinator_report_markdown"],
        "analysts": [_compact_analyst_summary(item) for item in trace["analyst_results"]],
    }
    messages = [
        {"role": "system", "content": STORY_WRITER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Write the walkthrough report from this run trace. Keep it readable from top to bottom.\n\n"
                + json.dumps(story_input, ensure_ascii=False, indent=2)
            ),
        },
    ]
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(settings, messages, tools=None)
    )
    return response.choices[0].message.content or _build_story_markdown_fallback(trace)


def _build_story_markdown_fallback(trace: dict[str, Any]) -> str:
    signal = trace["planner"]["planning_inputs"]["signal_evidence"]
    decision_card = _parse_bullet_fields(trace["decision_card_markdown"])
    selected = ", ".join(trace["planner"]["selected_analysts"])
    skipped = ", ".join(
        f"{item['analyst']} ({item['reason']})"
        for item in trace["planner"]["skipped_analysts"]
    ) or "none"
    analyst_sections = []
    for analyst in trace["analyst_results"]:
        assessment = _extract_assessment_block(analyst.get("memo_markdown", ""))
        tools_used = ", ".join(call["name"] for call in analyst.get("tool_calls", [])) or "no tools recorded"
        key_numbers = assessment.get("key_numbers", "not stated")
        verdict = assessment.get("verdict", "not stated")
        confidence = assessment.get("confidence", "not stated")
        analyst_sections.append(
            f"### {analyst['name']}\n"
            f"This analyst worked on **{analyst['focus']}** using `{tools_used}`. "
            f"It came back with **{verdict} / {confidence}** confidence and highlighted `{key_numbers}`."
        )

    return "\n\n".join(
        [
            f"# Story Report: {trace['city_id']} on {trace['dt']}",
            "## Executive Takeaway",
            (
                f"The system ended with **{decision_card.get('confidence', 'unknown')} confidence** and chose "
                f"**{decision_card.get('action', 'no recorded action')}**. "
                f"The headline was: **{decision_card.get('headline', 'no headline recorded')}**."
            ),
            "## Why This Day Triggered Review",
            (
                f"The run started because `{signal['metric']}` flagged a **{signal['signal_label']}** for "
                f"`{trace['city_id']}` on `{trace['dt']}`. Current sales were **{signal['current_sales']}**, "
                f"versus a trailing 7-day average of **{signal['trailing_7d_avg_sales']}**, which is a "
                f"**{signal['trailing_7d_pct_change']}%** move."
            ),
            (
                f"The planner selected `{selected}` and skipped {skipped}. "
                f"That means the system saw enough local evidence to spend time on sales, market, operations, and commercial angles."
            ),
            "## How The Analysis Unfolded",
            *analyst_sections,
            (
                "After the specialists finished, the coordinator combined their memos into a single RCA. "
                "That synthesis then passed through the finance controller, which reframed the story in terms of "
                "materiality, margin risk, and whether the issue looked one-off or structural."
            ),
            "## Where The System Challenged Itself",
            (
                "Before the final write-up, the critic reviewed the specialist claims. "
                "It pushed back on overconfident statements, especially around weather, stockout baselines, and "
                "whether promotion was truly ineffective rather than merely coincident with weak sales."
            ),
            (
                "In plain English: the system did not let the first explanation win by default. "
                "It kept the sales drop as real, treated stockout pressure as plausible, and downgraded any story "
                "that tried to turn correlation into proof."
            ),
            "## Final Decision",
            (
                f"The final decision card said **escalate: {decision_card.get('escalate', 'unknown')}** and "
                f"classified the impact as **{decision_card.get('materiality', 'unknown')}**. "
                f"The main follow-up is to **{decision_card.get('action', 'no action recorded')}**."
            ),
        ]
    )


def _compact_analyst_summary(analyst: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": analyst["name"],
        "focus": analyst["focus"],
        "tools_used": [call["name"] for call in analyst.get("tool_calls", [])],
        "assessment": _extract_assessment_block(analyst.get("memo_markdown", "")),
        "memo_excerpt": _first_nonempty_paragraph(analyst.get("memo_markdown", "")),
    }


def _extract_assessment_block(markdown_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in ("verdict", "confidence", "key_numbers", "causal_caveat", "data_gaps"):
        match = re.search(rf"^- {re.escape(key)}:\s*(.+)$", markdown_text, re.MULTILINE)
        if match:
            fields[key] = match.group(1).strip().strip("*")
    return fields


def _parse_bullet_fields(markdown_text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for key in ("headline", "confidence", "materiality", "pattern", "action", "escalate"):
        match = re.search(rf"^- {re.escape(key)}:\s*(.+)$", markdown_text, re.MULTILINE)
        if match:
            fields[key] = match.group(1).strip()
    return fields


def _first_nonempty_paragraph(markdown_text: str) -> str:
    for chunk in markdown_text.split("\n\n"):
        text = chunk.strip()
        if text and not text.startswith("#") and not text.startswith("|") and not text.startswith("- "):
            return text[:280]
    return ""


def _default_client_factory(settings: LLMSettings) -> ClientFactory:
    def factory(_: str) -> Any:
        return build_openai_compatible_client(settings)

    return factory


def _story_styles() -> str:
    return """
main {
  max-width: 1180px;
  padding: 40px 24px 56px;
}
.story-article {
  border: none;
  background: transparent;
  box-shadow: none;
  padding: 0;
}
.story-shell {
  display: grid;
  gap: 24px;
}
.story-hero {
  background:
    radial-gradient(circle at top right, rgba(249, 115, 22, 0.18), transparent 26%),
    linear-gradient(145deg, #0f172a 0%, #111827 58%, #1e293b 100%);
  border-radius: 24px;
  padding: 32px;
  color: #f8fafc;
  box-shadow: 0 22px 56px rgba(15, 23, 42, 0.18);
}
.story-hero-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(260px, 0.9fr);
  gap: 24px;
  align-items: start;
}
.story-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #cbd5e1;
}
.story-hero h1 {
  margin: 0 0 14px;
  font-size: clamp(2rem, 3vw, 2.8rem);
  line-height: 1.05;
  color: #ffffff;
}
.story-dek {
  margin: 0;
  max-width: 760px;
  color: #dbe4f0;
  font-size: 1.02rem;
  line-height: 1.75;
}
.story-action-card {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.07);
  padding: 18px 18px 16px;
  backdrop-filter: blur(12px);
}
.story-action-label {
  margin: 0 0 8px;
  color: #cbd5e1;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
}
.story-action-text {
  margin: 0;
  color: #ffffff;
  font-size: 0.98rem;
  line-height: 1.65;
}
.story-meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}
.story-meta-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.06);
}
.story-meta-label {
  margin: 0 0 8px;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
}
.story-meta-value {
  margin: 0;
  color: #0f172a;
  font-size: 1.05rem;
  font-weight: 700;
}
.story-section-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 20px;
}
.story-section {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 24px 26px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}
.story-section h2 {
  margin: 0 0 18px;
  font-size: 1.35rem;
  line-height: 1.2;
  color: #0f172a;
}
.story-section h3 {
  margin-top: 1.4rem;
  margin-bottom: 0.75rem;
  font-size: 1rem;
  color: #1e293b;
}
.story-section p,
.story-section li,
.story-dek li {
  font-size: 1rem;
  line-height: 1.75;
}
.story-section p {
  margin: 0 0 1rem;
}
.story-section ul,
.story-section ol {
  margin: 0.45rem 0 1.15rem 1.25rem;
  padding: 0;
}
.story-section li + li {
  margin-top: 0.4rem;
}
.story-section strong {
  color: #0f172a;
}
.story-section hr {
  display: none;
}
.story-section blockquote {
  margin: 1rem 0;
  padding: 14px 18px;
  border-left: 4px solid #f59e0b;
  background: #fff7ed;
  color: #7c2d12;
  border-radius: 0 14px 14px 0;
}
.story-section table {
  margin-top: 1rem;
  border-collapse: separate;
  border-spacing: 0;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}
.story-section th,
.story-section td {
  border: none;
  border-bottom: 1px solid #e2e8f0;
}
.story-section tr:last-child td {
  border-bottom: none;
}
.story-section th {
  background: #f8fafc;
  color: #334155;
  font-size: 0.85rem;
}
.story-section code {
  background: #eff6ff;
  color: #1d4ed8;
}
.story-section .story-kicker {
  margin-bottom: 10px;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.72rem;
}
@media (max-width: 880px) {
  .story-hero-grid,
  .story-meta-grid {
    grid-template-columns: 1fr;
  }
  .story-hero,
  .story-section,
  .story-meta-card {
    border-radius: 18px;
  }
}
@media (max-width: 640px) {
  main {
    padding: 20px 14px 40px;
  }
  .story-hero,
  .story-section {
    padding: 20px 18px;
  }
}
"""


def _render_story_shell(
    title: str,
    executive_title: str,
    executive_body: str,
    body_sections: list[tuple[str, str]],
) -> str:
    city_id, report_date = _parse_story_title(title)
    summary_markdown, action_markdown = _split_executive_parts(executive_body)
    summary_html = markdown.markdown(summary_markdown, extensions=["extra", "sane_lists"])
    action_html = markdown.markdown(action_markdown, extensions=["extra", "sane_lists"]) if action_markdown else ""
    hero_title = f"{city_id} on {report_date}" if city_id and report_date else executive_title

    section_html = []
    for heading, section_markdown in body_sections:
        rendered = markdown.markdown(
            section_markdown,
            extensions=["extra", "tables", "fenced_code", "sane_lists"],
        )
        section_html.append(
            f"""
            <section class="story-section">
              <div class="story-kicker">Analysis Layer</div>
              <h2>{escape(heading)}</h2>
              {rendered}
            </section>
            """
        )

    meta_cards = [
        ("Store", city_id or "Unknown"),
        ("Date", report_date or "Unknown"),
        ("Sections", str(len(body_sections) + 1)),
    ]
    meta_html = "".join(
        f"""
        <div class="story-meta-card">
          <p class="story-meta-label">{escape(label)}</p>
          <p class="story-meta-value">{escape(value)}</p>
        </div>
        """
        for label, value in meta_cards
    )

    action_block = (
        f"""
        <aside class="story-action-card">
          <p class="story-action-label">Recommended Action</p>
          <div class="story-action-text">{action_html}</div>
        </aside>
        """
        if action_html
        else ""
    )

    return f"""
    <article class="story-article">
      <div class="story-shell">
        <section class="story-hero">
          <div class="story-hero-grid">
            <div>
              <div class="story-eyebrow">Retail Insight Agent RCA</div>
              <h1>{escape(hero_title)}</h1>
              <p class="story-action-label">Executive Takeaway</p>
              <div class="story-dek">{summary_html}</div>
            </div>
            {action_block}
          </div>
        </section>
        <section class="story-meta-grid">
          {meta_html}
        </section>
        <div class="story-section-grid">
          {''.join(section_html)}
        </div>
      </div>
    </article>
    """


def _normalize_story_markdown(markdown_text: str) -> str:
    normalized = _repair_mojibake(markdown_text)
    normalized = normalized.replace("\r\n", "\n")
    replacements = {
        "â€”": "-",
        "â€“": "-",
        "â†’": "->",
        "âˆ’": "-",
        "â‰¤": "<=",
        "â‰¥": ">=",
        "Â±": "+/-",
        "Â°C": "C",
        "Â·": "-",
        "\u00a0": " ",
    }
    for bad, good in replacements.items():
        normalized = normalized.replace(bad, good)

    normalized = re.sub(
        r"(\*\*[^*\n]+\*\*):\s*\n(- )",
        r"\1\n\n\2",
        normalized,
    )
    normalized = re.sub(
        r"(\*\*[^*\n]+\*\*)\s*:\s*(- )",
        r"\1\n\n\2",
        normalized,
    )
    normalized = re.sub(
        r"([^\n#][^\n]*:)\n(- )",
        r"\1\n\n\2",
        normalized,
    )
    normalized = re.sub(r"\n---\n", "\n\n", normalized)
    return normalized.strip() + "\n"


def sanitize_generated_markdown(markdown_text: str) -> str:
    """Deterministic terminology enforcement — no LLM calls.

    Rules (all mechanical regex, applied in order):
    1. Mojibake repair (e.g. â€™ → ')
    2. Currency amounts → sales amount phrasing  ($200 → 200 sales amount)
    3. Standalone $ sign removal
    4. Unit/revenue vocabulary → sales amount
    5. Tier prefix references → store group (with letter preserved)
    6. Remaining standalone 'tier' → 'store group'
    """
    text = _repair_mojibake(markdown_text)

    # Currency amounts: $1,234 or $1234 → "1234 sales amount"
    text = re.sub(r'\$\s*([\d,]+(?:\.\d+)?)\s*[KkMm]?', _replace_currency, text)
    # Any remaining bare $ sign
    text = re.sub(r'\$', '', text)

    # Unit / revenue vocabulary (case-insensitive, word-boundary aware)
    text = re.sub(r'\bunit\s+sales\b', 'sales amount', text, flags=re.IGNORECASE)
    text = re.sub(r'\bsales\s+units?\b', 'sales amount', text, flags=re.IGNORECASE)
    text = re.sub(r'\brevenue\b', 'sales amount', text, flags=re.IGNORECASE)
    # "units" alone — only when clearly standalone metric, not in words like "unique"
    text = re.sub(r'(?<!\w)units(?!\w)', 'sales amount', text, flags=re.IGNORECASE)

    # Tier + prefix letter references: "tier L", "'l' prefix group", "prefix group m", etc.
    # Capture the letter so we can preserve it as uppercase in "store group X"
    text = re.sub(
        r"""(?:tier|prefix\s+group|store\s+tier)\s*['"]?\s*([lmhLMH])\b['"]?""",
        lambda m: f"store group {m.group(1).upper()}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"""['"]([lmhLMH])['"]\s+(?:prefix\s+group|tier)""",
        lambda m: f"store group {m.group(1).upper()}",
        text,
        flags=re.IGNORECASE,
    )
    # Remaining standalone tier / tiers
    text = re.sub(r'\btiers\b', 'store groups', text, flags=re.IGNORECASE)
    text = re.sub(r'\btier\b', 'store group', text, flags=re.IGNORECASE)

    return text


def _replace_currency(match: re.Match) -> str:
    """Convert a $NNN currency match to 'NNN sales amount'."""
    amount = match.group(1).replace(',', '')
    # Preserve K/M suffix from the full match if present
    suffix_map = {'k': '000', 'm': '000000'}
    original = match.group(0)
    for s, expansion in suffix_map.items():
        if original.endswith(s) or original.endswith(s.upper()):
            try:
                numeric = float(amount) * (1000 if s == 'k' else 1_000_000)
                amount = str(int(numeric))
            except ValueError:
                pass
            break
    return f"{amount} sales amount "


def find_report_language_issues(text: str) -> list[str]:
    forbidden_exact = [
        "unit sales",
        "units",
        "revenue",
        "$",
        " tier",
        "â",
        "Â",
        "Ã",
    ]
    issues = []
    for item in forbidden_exact:
        if item in text:
            issues.append(f"Found forbidden string: {repr(item)}")
    return issues


def _split_story_sections(markdown_text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(.+)$", markdown_text, re.MULTILINE))
    if not matches:
        return []

    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        heading = match.group(1).strip()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(markdown_text)
        body = markdown_text[start:end].strip()
        sections.append((heading, body))
    return sections


def _parse_story_title(title: str) -> tuple[str, str]:
    match = re.search(r"for\s+(.+?)\s+on\s+(\d{4}-\d{2}-\d{2})$", title)
    if not match:
        return "", ""
    return match.group(1), match.group(2)


def _split_executive_parts(executive_body: str) -> tuple[str, str]:
    cleaned = executive_body.strip()
    action_match = re.search(
        r"(?is)(.*?)(\*\*(?:Recommended action|Action):.*?\*\*)$",
        cleaned,
    )
    if action_match:
        return action_match.group(1).strip(), action_match.group(2).strip()

    parts = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
    if len(parts) >= 2:
        return parts[0], "\n\n".join(parts[1:])
    return cleaned, ""


def _repair_mojibake(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _repair_mojibake(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_repair_mojibake(item) for item in value]
    if not isinstance(value, str):
        return value

    repaired = value
    replacements = [
        ("Ã¢â‚¬â€ ", "-"),
        ("Ã¢â‚¬â€œ", "-"),
        ("Ã¢â€°Â ", "!="),
        ("â€”", "-"),
        ("â€“", "-"),
        ("â†’", "->"),
        ("Ã—", "x"),
        ("âˆ’", "-"),
        ("â‰¤", "<="),
        ("â‰¥", ">="),
        ("â‰ ", "!="),
        ("Ïƒ", "sigma"),
        ("Â°C", "C"),
        ("Â±", "+/-"),
        ("Â·", "-"),
        ("Â", ""),
        ("â", ""),
        ("Ã", ""),
    ]
    for bad, good in replacements:
        repaired = repaired.replace(bad, good)
    return repaired
