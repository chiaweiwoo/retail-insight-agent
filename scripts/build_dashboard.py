"""Generate a self-contained dashboard HTML from analysis CSVs and run_logs.duckdb."""

import csv
import json
import pathlib

import duckdb

ROOT = pathlib.Path(__file__).parent.parent
ANALYSIS = ROOT / "data" / "analysis"
LOG_DB_PATH = ROOT / "data" / "db" / "run_logs.duckdb"
OUT = ROOT / "ui" / "dashboard.html"

THRESHOLD = 20


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def load_grid():
    path = ANALYSIS / "trigger_grids" / f"trailing_7d_pct_trigger_grid_{THRESHOLD}.csv"
    rows = read_csv(path)
    stores = [r["store_alias"] for r in rows]
    dates = [k for k in rows[0].keys() if k != "store_alias"]
    cells = {r["store_alias"]: {d: r[d] for d in dates} for r in rows}
    return stores, dates, cells


def load_store_stats():
    rows = read_csv(ANALYSIS / "pct_trigger_by_store.csv")
    return {
        r["store_alias"]: r
        for r in rows
        if r["metric"] == "trailing_7d_pct_change" and int(r["pct_threshold"]) == THRESHOLD
    }


def load_summary():
    rows = read_csv(ANALYSIS / "pct_trigger_overall_summary.csv")
    for r in rows:
        if r["metric"] == "trailing_7d_pct_change" and int(r["pct_threshold"]) == THRESHOLD:
            return r
    return {}


def build_html(stores, dates, cells, store_stats, summary, recent_runs=None):
    data = {
        "threshold": THRESHOLD,
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
  /* Per-store bars */
  .store-bars {{ display: flex; flex-direction: column; gap: 5px; margin-bottom: 28px; }}
  .store-row {{ display: flex; align-items: center; gap: 10px; height: 24px; }}
  .store-label {{ width: 48px; text-align: right; font-size: 11px; color: var(--muted); flex-shrink: 0; }}
  .bar-track {{ flex: 1; height: 14px; background: var(--neutral); border-radius: 3px; display: flex; overflow: hidden; position: relative; }}
  .bar-drop {{ background: var(--drop); height: 100%; }}
  .bar-lift {{ background: var(--lift); height: 100%; }}
  .store-rate {{ width: 40px; font-size: 11px; color: var(--muted); flex-shrink: 0; }}
  /* Grid */
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
  /* Recent runs */
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
  <p>Trailing 7-day % change &gt; {THRESHOLD}% threshold &nbsp;·&nbsp; <span id="date-range"></span></p>
</header>

<div class="summary-bar" id="summary-bar"></div>

<div class="main">
  <p class="section-title">Drop / Lift days per store</p>
  <div class="store-bars" id="store-bars"></div>

  <p class="section-title">Store × Date signal grid</p>
  <div class="grid-wrap">
    <table class="grid-table" id="grid-table"></table>
  </div>

  <div class="legend">
    <div class="legend-item"><div class="legend-swatch" style="background:var(--drop)"></div>Drop (&gt;{THRESHOLD}% below 7d avg)</div>
    <div class="legend-item"><div class="legend-swatch" style="background:var(--lift)"></div>Lift (&gt;{THRESHOLD}% above 7d avg)</div>
    <div class="legend-item"><div class="legend-swatch" style="background:var(--neutral)"></div>No signal</div>
  </div>

  <p class="section-title" style="margin-top:32px">Recent pipeline runs</p>
  <div id="runs-section"></div>
</div>

<script>
const DATA = {data_json};

(function () {{
  const {{ stores, dates, cells, store_stats, summary }} = DATA;

  // Date range label
  document.getElementById("date-range").textContent =
    dates[0] + " – " + dates[dates.length - 1];

  // Summary bar
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

  // Per-store bars
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

  // Recent runs
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
        <td class="run-path">${{r.output_dir || "—"}}</td>
      `;
    }});
    runsEl.appendChild(t);
  }}

  // Grid
  const table = document.getElementById("grid-table");

  // Header row with date labels (show month label on first of month)
  const thead = table.createTHead();
  const hrow = thead.insertRow();
  // empty corner
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
      // show month name on 1st of month
      const monthNames = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
      th.textContent = monthNames[parseInt(mm)];
      lastMonth = mm;
    }}
    // show day number every 7 days starting day 1
    if (parseInt(dd) === 1 || parseInt(dd) % 7 === 0) {{
      if (!isMonthStart) th.textContent = dd;
    }}
    hrow.appendChild(th);
  }});

  // Data rows
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


def load_recent_runs(limit=20):
    if not LOG_DB_PATH.exists():
        return []
    con = duckdb.connect(str(LOG_DB_PATH), read_only=True)
    rows = con.execute(f"""
        SELECT
            run_name,
            MIN(timestamp_sgt) AS started_at,
            COUNT(*)           AS events,
            MAX(CASE WHEN action = 'completed' AND actor_name = 'manager_pipeline'
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


def main():
    stores, dates, cells = load_grid()
    store_stats = load_store_stats()
    summary = load_summary()
    recent_runs = load_recent_runs()
    html = build_html(stores, dates, cells, store_stats, summary, recent_runs)
    OUT.write_text(html, encoding="utf-8")
    print(f"Dashboard written to {OUT}")


if __name__ == "__main__":
    main()
