# CLAUDE.md

Read `README.md` first for the current workflow.

## Useful Commands

```bash
uv run python -m rca.cli build                         # ingest parquet → push all tables to Supabase
uv run python -m rca.cli analyze                       # compute business-target deviations → push rca_city_signal
uv run python -m rca.cli profile                       # build data/context_pack.json from Supabase
uv run python -m rca.cli run --city 0                  # scan triggered dates, run oldest→latest
uv run python -m rca.cli run --city 0 --dt 2024-05-16  # single-day override
uv run python -m rca.cli run --city 0 --dt 2024-05-16 --dry-run --full
uv run python -m rca.cli run --city 0 --dt 2024-05-16 --dry-run --reflect  # adds reflection pass
uv run python -m rca.cli bench
uv run python -m rca.cli eval --dry-run
uv run python -m rca.cli story --run-dir data/analysis/agent_benchmark_runs/<run_folder>
uv run python -m rca.cli runs
uv run python -m rca.cli distil --city 0             # generate city memory profile
uv run python -m rca.cli distil                      # distil all cities with history
uv run python -m rca.cli reset-memory --city 0       # delete one city's profile
uv run python -m rca.cli reset-memory --all          # delete all profiles
uv run python -m rca.cli mcp                         # start the FastMCP server
```

## Important Behavior

- `rca run` prints the decision card by default.
- `--full` also prints the drill-down RCA.
- `--dry-run` uses the deterministic stub client and should exercise the whole pipeline.
- `rca story` reads a saved trace and writes root-level story report files.
- `sale_amount` and `hours_sale` are normalized sales amounts from the source dataset, not currency. Prefer `sales amount`.
- **Model Routing**: Specialists run on the fast model (e.g., flash), while synthesis/oversight (critic, coordinator, controller, slt) run on the deep model (e.g., pro).
- **Deterministic Sanitizer**: The `sanitize` node uses no LLM calls. It runs strictly once at the write boundary before pushing to Supabase.

## Data Architecture

Three-layer split:

| Layer | Tables | Updated by |
| --- | --- | --- |
| **Fixed / precomputed** | `rca_city_series`, `rca_city_hourly`, `rca_city_normals`, `rca_finance_forecast`, `rca_city_segment`, `rca_city_correlations` | `rca build` (offline ETL) |
| **Precomputed triggers** | `rca_city_signal` | `rca analyze` — actual vs business target, all 1620 city-days |
| **Agent output** | `rca_outcome`, `rca_city_profile` | `rca run` / `rca story` / `rca distil` |

**Signal trigger**: Business target = `rca_finance_forecast.forecast_sales × BUSINESS_TARGET_GROWTH_FACTOR` (default 1.03). Drop ≤ −10%, Lift ≥ +25% vs business target. Thresholds live in `config.py` only — not in SQL. STL is gone.

**Runbook**: `rca build` → `rca analyze` → `rca run --city N` → `rca distil --city N`

**No local database**: DuckDB is fully removed. `rca build` reads parquet from disk and pushes directly to Supabase. All agent runtime reads go to Supabase.

## Artifacts & Datastores

Non-quick runs write decision cards, run traces, specialist memos, and logs to `data/analysis/agent_benchmark_runs/`.

**Supabase is the sole system of record** (`rca_` prefixed tables, project: hzxjiwvihujybxlaklle, ap-southeast-1).

## Sandbox Caveats

The local dataset covers 18 cities (city IDs 0–17), 90 days (2024-03-28 to 2024-06-25). "Peer group" comparisons are statistically noisy — only 18 cities total. Do not let agents over-index on peer comparisons without acknowledging this limitation.
