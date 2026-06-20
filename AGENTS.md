# AGENTS.md

Working notes and strict guardrails for the RCA agent system.

## Guardrails

- Calibration matters more than eloquence.
- Every node must change the output in a visible way.
- Claims must stay tied to evidence we actually have.
- Margin is a risk lens here, not a computed metric.
- The evaluator is separate from the critic.

## Data Scale Limitations

- **Dataset**: `FreshRetailNet-50K` heavily normalizes sales figures.
- **Sandbox**: Local dataset aggregates data to the City level. "Peer group" comparisons between cities are statistically noisy. Analysts must acknowledge this.
- **Source of Truth**: Supabase is the sole system of record and compute. DuckDB has been fully deprecated and removed. All analytical tools read directly from Supabase tables (`rca_` prefix).

## The LangGraph Pipeline

Orchestration is handled by LangGraph via `RcaState`.

1. **Build context**: Fetch from Supabase.
2. **Retrieve memory**: Fetch `rca_store_profile` (now mapping cities) and recent `rca_outcome` rows.
3. **Plan (Fast Model)**: Dispatch specialists.
4. **Specialists (Fast Model, Parallel)**: Run `sales_analyst`, `ops_analyst`, `commercial_analyst`, `market_analyst`.
5. **Critic (Deep Model)**: Downgrades claims, flags correlation-as-cause.
6. **Coordinator (Deep Model)**: Synthesizes memos.
7. **Controller (Deep Model)**: Frames margin risk.
8. **SLT Brief (Deep Model)**: Produces the Decision Card.
9. **Record**: Save to Supabase `rca_outcome`.

## Tool Access

All tools read directly from Supabase `rca_` tables.

| Agent | Tools |
| --- | --- |
| `sales_analyst` | `get_signal_evidence`, `get_sales_context` |
| `ops_analyst` | `get_stockout_context`, `get_stockout_baseline`, `get_sales_context` |
| `commercial_analyst` | `get_discount_context`, `get_activity_context`, `get_sales_context` |
| `market_analyst` | `get_calendar_weather_context`, `get_peer_store_context`, `get_sales_context` |

## The Dashboard

The UI is a Next.js App Router deployed on Vercel (`dashboard/`). It uses a premium glassmorphism design system built with pure Tailwind CSS v4, Lucide icons, and Recharts.
- `/` -> Fleet Overview with a 14-day trailing signal heatmap grid and drop/lift badges.
- `/cities/[storeId]` -> Detailed regional telemetry featuring a responsive Recharts AreaChart with RCA triggers overlaid.
- `/cities/[storeId]/rca` -> Historical Decision Cards rendered in elegant glass panels.
- `/cities/[storeId]/profile` -> Distilled semantic memory displayed in a rich icon grid.
The dashboard reads securely from Supabase using Row Level Security (RLS) and the anon key.

## Shipped Ecosystem Features

- **MCP Runtime**: Start the FastMCP server with `uv run python -m rca.cli mcp` to expose our Supabase evidence tools to any external LLM interface.
- **Skills**: Claude skills are provided in `.claude/skills/` to automate tasks like story report generation and RCA running.

## Out Of Scope

- Product/category drilldown.
- Customer analysis.
