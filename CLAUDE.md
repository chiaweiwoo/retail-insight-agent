# CLAUDE.md

Architecture, agent roles, commands, and data layout: **README.md**.
Agent guardrails and out-of-scope boundaries: **AGENTS.md**.

Read both before making non-trivial changes.

## Dashboard

`ui/public/dashboard.html` is a generated file — do not edit it directly.
Rebuild it with:

```bash
uv run python -m rca.cli dashboard
```

Source: `rca/report.py::build_dashboard_html`
Data inputs: `data/analysis/trigger_grids/trailing_7d_pct_trigger_grid_20.csv`, related CSVs under `data/analysis/`, and `data/runs.duckdb` for the Recent Runs section.

## Run Logs

All pipeline runs write events to `data/runs.duckdb` (table `run_log_event`). Created automatically on first run. To view recent runs in the terminal:

```bash
uv run python -m rca.cli runs
```

## DB Migration

If upgrading from the old structure, copy the old database to the new path:

```bash
cp data/db/rca_foundry.duckdb data/rca.duckdb
```
