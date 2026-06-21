# CLAUDE.md

Read `README.md` first for the current workflow.

## Useful Commands

```bash
uv run python -m rca.cli build                         # ingest parquet → push base tables to Supabase
uv run python -m rca.cli signal                        # materialize rca.signals from ingested tables
uv run python -m rca.cli run --city 0 --date 2024-04-01          # run RCA for one city/date
uv run python -m rca.cli run --city 0 --date 2024-04-01 --dry-run # stub client, no real LLM
uv run python -m rca.cli replay --city 0               # reset + rerun all signal dates + review
uv run python -m rca.cli replay --city 0 --dry-run --limit 3     # dry-run first 3 dates
uv run python -m rca.cli replay --city 0 --no-reset    # rerun without deleting existing data
uv run python -m rca.cli replay --city 0 --no-review   # skip alignment reviewer
uv run python -m rca.cli mcp                           # start the FastMCP tool server
```

## Important Behavior

- `rca build` reads parquet from disk and pushes base city/date tables to Supabase. Run before `rca signal`.
- `rca signal` rebuilds `rca.signals` from the ingested tables. **Must be re-run after any migration that drops/recreates `rca.signals`.**
- `rca run` runs a single city/date through the bounded LangGraph investigation loop.
- `--dry-run` uses the deterministic stub client and exercises the whole pipeline without a real LLM.
- `rca replay --reset` (default) deletes outcomes, events, completions, memory, evidence_cache, and external_events for the city before replaying — destructive, gives a clean cold-start batch.
- `rca replay` stores per-date quality scores in `rca.replay_review` for incremental improvement tracking.
- **Model Routing**: Specialists run on the fast model; planner, critic, coordinator, reviewer run on the deep model.
- `sale_amount` and `hours_sale` are normalized sales amounts from the source dataset, not currency.

## Data Architecture

Three-layer split:

| Layer | Tables | Updated by |
| --- | --- | --- |
| **Fixed / precomputed** | `rca.sales`, `rca.inventory`, `rca.pricing`, `rca.promotions`, `rca.calendar`, `rca.weather`, `rca.goals` | `rca build` |
| **Precomputed triggers** | `rca.signals` | `rca signal` |
| **Agent output** | `rca.outcomes`, `rca.memory`, `rca.events`, `rca.completions`, `rca.evidence_cache`, `rca.external_events`, `rca.replay_review` | `rca run` / `rca replay` |

**Signal trigger**: Drop ≤ −10%, Lift ≥ +25% vs synthetic business goal. Thresholds live in `config.py` only — not in SQL.

**Runbook**: `rca build` → `rca signal` → `rca run --city N --date YYYY-MM-DD` (or `rca replay --city N`)

**Supabase is the sole system of record** (`rca` schema, all tables prefixed accordingly).

## Sandbox Caveats

The local dataset covers 18 cities (city IDs 0–17), 90 days (2024-03-28 to 2024-06-25). "Peer group" comparisons are statistically noisy — only 18 cities total. Do not let agents over-index on peer comparisons without acknowledging this limitation.
