# Retail Insight Agent v2

Retail Insight Agent is a learning project for building an evidence-backed retail RCA system with a stronger autonomous-agent harness.

The v2 direction is:

- city/date evidence only
- rawer business facts in Supabase
- agent-side reasoning at runtime
- internal plus external factor investigation
- simple dashboard for signals, results, memory, and logs

## Public CLI

```bash
uv run python -m rca.cli build
uv run python -m rca.cli signal
uv run python -m rca.cli run --city 0 --date 2024-06-09
uv run python -m rca.cli mcp
```

## Architecture

- `rca build`
  - reads the FreshRetailNet parquet
  - resets and repopulates the base RCA tables
  - aggregates facts to city/date grain
  - builds synthetic expected-sales goals

- `rca signal`
  - reads the ingested `sales`, `goals`, and `calendar` tables
  - materializes `rca.signals`
  - keeps signal tuning separate from stable ingestion

- `rca run`
  - retrieves signal evidence and city memory from Supabase
  - runs a bounded LangGraph investigation loop (up to 5 rounds by default)
  - each round: planner selects agents → agents run in parallel → evidence accumulates → critic reviews and decides whether to continue
  - produces a structured DecisionBrief with RCA, prediction, and prescription sections
  - evaluates output with 8 deterministic audit checks and a 0-to-1 quality score
  - distils reusable lessons into city memory
  - stores the full outcome (decision brief, evidence ledger, investigation rounds, evaluation) in Supabase

- `rca mcp`
  - exposes the evidence tools through FastMCP for learning and experimentation

## Data Guardrails

- `sale_amount` is a normalized sales amount, not currency.
- `activity_flag` is unlabeled and should be treated cautiously.
- holiday names are inferred, not source-labeled.
- no product or store drilldown is part of the v2 runtime.

## Supabase

Use schema `rca`.

Before running the app, apply the migration in [20260621_retail_rca_0011_v2_schema.sql](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/supabase/migrations/20260621_retail_rca_0011_v2_schema.sql) and make sure the `rca` schema is exposed through the Supabase Data API for dashboard reads.

For write-heavy runtime tables that use `bigserial` ids, also grant sequence access to `service_role`:

```sql
grant usage, select, update on all sequences in schema rca to service_role;
```

## Dashboard

The dashboard keeps the surface intentionally small:

- city signal heatmap from `rca.signals`
- city timeline of actual sales vs synthetic business goal
- clickable drop/lift markers
- RCA page with root cause, prediction, and prescription
- logs page for events, completions, and tool-call traces
- memory page for distilled lessons

## Learning Notes

See:

- [AGENT_SYSTEM_OVERVIEW.md](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/docs/AGENT_SYSTEM_OVERVIEW.md)
- [AGENT_SYSTEM_DESIGN.md](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/docs/AGENT_SYSTEM_DESIGN.md)
- [0001-v2-core-decisions.md](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/docs/adr/0001-v2-core-decisions.md)
- [0002-agentic-investigation-upgrade.md](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/docs/adr/0002-agentic-investigation-upgrade.md)
- [0003-level-5-learning-mode-agent.md](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/docs/adr/0003-level-5-learning-mode-agent.md)
- [PRD.md](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/docs/PRD.md)
