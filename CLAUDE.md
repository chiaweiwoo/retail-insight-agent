# CLAUDE.md

Project documentation lives in **README.md** (architecture, agent roles, commands, benchmarks).
Agent constraints and guardrails live in **AGENTS.md**.

Read both before making non-trivial changes.

## Dashboard

`ui/dashboard.html` is a generated file — do not edit it directly.
Rebuild it by running:

```
uv run python scripts/build_dashboard.py
```

Source: `scripts/build_dashboard.py`
Data: `data/analysis/trigger_grids/trailing_7d_pct_trigger_grid_20.csv`, related CSVs under `data/analysis/`, and `data/db/run_logs.duckdb` for the Recent Runs section.

## Run Logs

All pipeline runs write events to `data/db/run_logs.duckdb` (table `run_log_event`). The file is created automatically on first run. To view recent runs in the terminal: `uv run python scripts/show_runs.py`.
