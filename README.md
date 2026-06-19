# Retail Insight Agent

Retail Insight Agent is a personal learning project for building an evidence-backed retail RCA workflow.

The current implementation milestone is intentionally narrow:

- Phase 1 only: ingest scoped raw data into DuckDB.
- Validate the resulting daily tables.
- Stop before RCA logic, UI, agents, or LLM features.

## Current Scope

- Source dataset: FreshRetailNet-50K `train.parquet`
- City scope: `city_id = 0`
- Store scope: 15 mapped store aliases
- Output: `data/db/rca_foundry.duckdb`

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
```

## Commands

```bash
uv run python scripts/ingest_daily_tables.py
uv run python scripts/validate_daily_tables.py
```

## Notes

- The committed database artifact is the clean analytical output.
- The raw parquet file is expected locally at `data/raw/train.parquet` and is not committed.
- UI is planned for a later phase after the DuckDB evidence layer is stable.
