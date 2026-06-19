# Retail Insight Agent

Retail Insight Agent is a personal learning project for building an evidence-backed retail RCA workflow.

Current implemented milestones:

- Phase 1: scoped raw data ingested into DuckDB
- Milestone B: reliability checks plus a read-only evidence viewer
- Still out of scope: RCA narrative generation, agents, LangGraph, and LLM features

## Current Scope

- Source dataset: FreshRetailNet-50K `train.parquet`
- City scope: `city_id = 0`
- Store scope: 15 mapped store aliases
- Trusted artifact for tests and UI: `data/db/rca_foundry.duckdb`
- Read-only UI: store/date evidence viewer over exported DuckDB data

## Project Layout

```text
retail-insight-agent/
  AGENTS.md
  README.md
  docs/
    PRD.md
    UI_PLAN.md
  data/
    raw/
      train.parquet
      train_metadata.json
    db/
      rca_foundry.duckdb
  scripts/
    ingest_daily_tables.py
    export_ui_data.py
    validate_daily_tables.py
  sql/
    migrations/
      001_create_daily_tables.sql
    queries/
      preview_store_day.sql
  src/
    rca_foundry/
      __init__.py
      config.py
      db.py
      ingestion.py
      query.py
      validation.py
  tests/
    test_query.py
    test_validation.py
  ui/
    public/
      evidence_data.json
    src/
      main.js
      style.css
```

## Commands

```bash
uv run python scripts/ingest_daily_tables.py
uv run python scripts/validate_daily_tables.py
uv run python scripts/analyze_sales_signals.py
uv run pytest
uv run python scripts/export_ui_data.py
cd ui
npm install
npm run dev
```

## Notes

- The committed database artifact is the clean analytical output and the current test input.
- The raw parquet file is expected locally at `data/raw/train.parquet` and is not committed.
- Sales-signal exploration outputs are written to `data/analysis/` and `docs/analysis/`.
- Important analytical decisions should be reflected in `README.md`, `AGENTS.md`, `docs/PRD.md`, and the detailed note under `docs/analysis/`.
- The UI is an evidence viewer only. It does not generate RCA conclusions.
- CI runs validation, tests, UI data export, and UI build from the committed DuckDB.
