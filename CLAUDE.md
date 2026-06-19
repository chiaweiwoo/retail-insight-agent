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
Data: `data/analysis/trigger_grids/trailing_7d_pct_trigger_grid_20.csv` and related CSVs under `data/analysis/`.
