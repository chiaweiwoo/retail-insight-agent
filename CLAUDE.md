# CLAUDE.md

Read `README.md` first for the current workflow.

## Useful Commands

```bash
uv run python -m rca.cli build                          # ingest parquet and push base tables to Supabase
uv run python -m rca.cli signal                         # materialize rca.signals from ingested tables
uv run python -m rca.cli run --city 0 --date 2024-04-01 # run RCA for one city/date
uv run python -m rca.cli simulate --city 0              # cold-start city simulation across all signal dates
uv run python -m rca.cli mcp                            # start the FastMCP tool server
```

## Important Behavior

- `rca build` reads parquet from disk and pushes base city/date tables to Supabase. Run before `rca signal`.
- `rca signal` rebuilds `rca.signals` from the ingested tables. Re-run after any migration that drops/recreates `rca.signals`.
- `rca run` runs a single city/date through the bounded LangGraph investigation loop.
- `rca simulate` always deletes prior outcomes, events, completions, memory, evidence_cache, and external_events for the city before running. It is a cold-start batch simulation by design.
- Model routing: specialists run on the fast model; planner, critic, coordinator, reviewer run on the deep model.
- `sale_amount` and `hours_sale` are normalized sales amounts from the source dataset, not currency.

## Data Architecture

Three-layer split:

| Layer | Tables | Updated by |
| --- | --- | --- |
| Fixed / precomputed | `rca.sales`, `rca.inventory`, `rca.pricing`, `rca.promotions`, `rca.calendar`, `rca.weather`, `rca.goals` | `rca build` |
| Precomputed signals | `rca.signals` | `rca signal` |
| Agent output | `rca.outcomes`, `rca.memory`, `rca.events`, `rca.completions`, `rca.evidence_cache`, `rca.external_events`, `rca.replay_review` | `rca run` / `rca simulate` |

Signal trigger: drop <= -10%, lift >= +25% vs synthetic business goal. Thresholds live in `config.py` only, not in SQL.

Runbook: `rca build` -> `rca signal` -> `rca run --city N --date YYYY-MM-DD` or `rca simulate --city N`.

Supabase is the sole system of record (`rca` schema).

## Dashboard Inspection Surfaces

- `/` for city/date signals
- `/cities/[cityId]` for actual vs goal trend and clickable signal markers
- `/cities/[cityId]/rca` for final decision output
- `/cities/[cityId]/simulate` for simulation-review batches from `rca simulate`
- `/cities/[cityId]/logs` for workflow and completion traces
- `/cities/[cityId]/profile` for distilled memory

## Sandbox Caveats

The local dataset covers 18 cities (city IDs 0-17), 90 days (2024-03-28 to 2024-06-25). Peer group comparisons are statistically noisy because there are only 18 cities total. Do not let agents over-index on peer comparisons without acknowledging this limitation.
