from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path

import duckdb
import markdown


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


_DASHBOARD_THRESHOLD = 20


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_grid(analysis_dir: Path) -> tuple[list[str], list[str], dict]:
    path = analysis_dir / "trigger_grids" / f"trailing_7d_pct_trigger_grid_{_DASHBOARD_THRESHOLD}.csv"
    rows = _read_csv(path)
    stores = [r["store_alias"] for r in rows]
    dates = [k for k in rows[0].keys() if k != "store_alias"]
    cells = {r["store_alias"]: {d: r[d] for d in dates} for r in rows}
    return stores, dates, cells


def _load_store_stats(analysis_dir: Path) -> dict:
    rows = _read_csv(analysis_dir / "pct_trigger_by_store.csv")
    return {
        r["store_alias"]: r
        for r in rows
        if r["metric"] == "trailing_7d_pct_change" and int(r["pct_threshold"]) == _DASHBOARD_THRESHOLD
    }


def _load_summary(analysis_dir: Path) -> dict:
    rows = _read_csv(analysis_dir / "pct_trigger_overall_summary.csv")
    for r in rows:
        if r["metric"] == "trailing_7d_pct_change" and int(r["pct_threshold"]) == _DASHBOARD_THRESHOLD:
            return r
    return {}


def _load_recent_runs(log_db_path: Path, limit: int = 20) -> list[dict]:
    if not log_db_path.exists():
        return []
    con = duckdb.connect(str(log_db_path), read_only=True)
    rows = con.execute(f"""
        SELECT
            run_name,
            MIN(timestamp_sgt) AS started_at,
            COUNT(*)           AS events,
            MAX(CASE WHEN action = 'completed' AND actor_name = 'coordinator_pipeline'
                     THEN details_json END) AS completed_json
        FROM run_log_event
        GROUP BY run_name
        ORDER BY MIN(timestamp_sgt) DESC
        LIMIT {limit}
    """).fetchall()
    con.close()
    result = []
    for run_name, started_at, events, completed_json in rows:
        output_dir = None
        if completed_json:
            details = json.loads(completed_json)
            output_dir = details.get("output_dir")
        result.append({
            "run_name": run_name,
            "started_at": started_at,
            "events": events,
            "output_dir": output_dir,
        })
    return result


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
    {{ label: "Trigger rate", value: (summary.triggered_store_days / summary.eligible_store_days * 100).toFixed(1) + "%", cls: "" }},
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


def build_dashboard_html(output_path: Path) -> None:
    """Build the dashboard HTML from analysis CSVs and run logs."""
    from rca.config import ANALYSIS_PATH, LOG_DB_PATH

    stores, dates, cells = _load_grid(ANALYSIS_PATH)
    store_stats = _load_store_stats(ANALYSIS_PATH)
    summary = _load_summary(ANALYSIS_PATH)
    recent_runs = _load_recent_runs(LOG_DB_PATH)

    html = _build_dashboard_html_content(stores, dates, cells, store_stats, summary, recent_runs)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")


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
