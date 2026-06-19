# AGENTS.md - Retail Insight Agent Coding Instructions

## Project

Retail Insight Agent is a personal learning project to build an evidence-backed retail RCA system.

Current implementation milestone:

```text
Phase 1 complete: local data ingestion into DuckDB.
Milestone B in progress: reliability checks and a read-only evidence viewer.
Milestone C setup: signal exploration for daily store RCA triggers.
```

Do not build agent logic or generated narrative in this milestone.

## Hard Rules

Do not implement any of the following in this phase:

```text
autonomous agents
LangGraph
MCP
skills
web search
news agent
LLM calls
persistent memory
FastAPI
Streamlit
dashboard
notebooks
product/category drilldown
customer analysis
RCA report generation
```

Allowed in Milestone B:

```text
read-only evidence UI over committed DuckDB output
tests and CI
query/export helpers
precomputed signal exploration and trigger analysis
```

Keep the implementation read-only and evidence-first.

Important project decisions should be documented when they are made:

```text
update README.md for operator-facing workflow
update AGENTS.md for implementation constraints
update docs/PRD.md for product-level intent
add or refresh docs/analysis notes for metric or threshold decisions
```

Current signal exploration direction:

```text
daily grain = one store on one date
signals should be precomputed because the dataset slice is fixed
drop/lift triggers are per store, not one global daily trigger
current working metric = trailing_7d_pct_change
current discussion thresholds = drop <= -20%, lift >= +30%
maintain a fixed early RCA test bench in docs/analysis/rca_test_scenarios.md
```

## Package Manager

Use `uv`.

Expected commands:

```bash
uv add pandas duckdb pyarrow
uv run python scripts/ingest_daily_tables.py
uv run python scripts/validate_daily_tables.py
```

Use Python 3.11 or above.

## Expected Project Structure

```text
retail-insight-agent/
  AGENTS.md
  README.md
  pyproject.toml
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
```

## Raw Data

Expected raw file:

```text
data/raw/train.parquet
```

Supporting metadata file:

```text
data/raw/train_metadata.json
```

Raw grain:

```text
city_id + store_id + product_id + dt
```

Only use:

```text
city_id = 0
```

## Store Mapping

Use only these stores.

```python
STORE_MAP = {
    "h235": 235,
    "h263": 263,
    "h182": 182,
    "h018": 18,
    "h555": 555,
    "m679": 679,
    "m648": 648,
    "m041": 41,
    "m236": 236,
    "m386": 386,
    "l260": 260,
    "l185": 185,
    "l165": 165,
    "l164": 164,
    "l175": 175,
}
```

Expose only `store_alias` in final analytical tables.

Do not include `city_id` in final tables.

## Output Database

Create DuckDB file:

```text
data/db/rca_foundry.duckdb
```

If the database already exists, rebuild it cleanly.

## Required Tables

Create these seven tables:

```text
dim_store
dim_holiday_day
dim_weather_day
fact_sales_store_day
fact_stockout_store_day
fact_discount_store_day
fact_activity_store_day
```

Do not create a combined mart table.

## Validation Requirements

Validation must check:

1. DuckDB file exists.
2. All seven tables exist.
3. Row counts are correct.
4. No null `store_alias`.
5. No null `dt`.
6. Each fact table has exactly 15 stores.
7. Each fact table has exactly 90 dates.
8. Rate columns are between 0 and 1.
9. Hourly sales columns are non-negative.
10. Validation summary is printed clearly.

## Coding Style

Keep the implementation simple.

Use:

```text
pandas
duckdb
pyarrow
pathlib
```

Raise clear errors if:

```text
raw parquet is missing
required columns are missing
row counts are wrong
hourly arrays are malformed
```

## Stop Condition

After signal exploration is documented and the next implementation target is clear, stop.
