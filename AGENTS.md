# AGENTS.md

Working notes and guardrails for the v2 RCA agent system.

## Guardrails

- Calibration matters more than eloquence.
- Every node must change the output in a visible way.
- Claims must stay tied to evidence we actually have.
- Margin is a risk lens here, not a computed metric.
- External evidence is supportive unless it clearly aligns with internal facts.

## Data Scale Limitations

- **Dataset**: `FreshRetailNet-50K` heavily normalizes sales figures.
- **Runtime Grain**: All runtime evidence is city/date only.
- **Cross-city caution**: Peer-style comparisons across cities are weak priors, not strong proof.
- **Source of truth**: Supabase is the sole runtime system of record. DuckDB is gone from runtime entirely.
- **Scope rule**: Product and store detail never survive into runtime tables. If the source contains store or product rows, we aggregate them into city/day facts such as counts, totals, rates, and intraday profiles.

## Public CLI

- `uv run python -m rca.cli build`
- `uv run python -m rca.cli run --city <id> --date <YYYY-MM-DD>`
- `uv run python -m rca.cli mcp`

## The LangGraph Pipeline

Orchestration is handled by LangGraph via `RcaState`.

1. **Plan**: Read the signal, recent context, and memory; decide which agents to run.
2. **Specialists (Parallel)**: Run the chosen internal agents plus the news agent when useful.
3. **Critic**: Downgrade weak claims and flag correlation-as-cause leaps.
4. **Coordinator**: Build the decision card, RCA, prediction, and prescription.
5. **Memory Distiller**: Save reusable lessons for later runs.
6. **Record**: Persist outcomes, logs, completions, and memory in Supabase.

## Tool Access

All tools read directly from Supabase `rca.*` tables.

| Agent | Tools |
| --- | --- |
| `statistician` | `compare_recent_baseline`, `compare_same_weekday_baseline`, `detect_intraday_shift` |
| `sales_agent` | `get_signal_evidence`, `get_sales_context` |
| `inventory_agent` | `get_inventory_context`, `get_intraday_profile`, `compare_recent_baseline` |
| `pricing_agent` | `get_pricing_context`, `get_signal_evidence` |
| `promotions_agent` | `get_promotions_context`, `get_signal_evidence` |
| `calendar_weather_agent` | `get_calendar_weather_context`, `get_signal_evidence` |
| `news_agent` | `search_external_events`, `get_signal_evidence` |

## Runtime Tables

- `rca.sales`
- `rca.inventory`
- `rca.pricing`
- `rca.promotions`
- `rca.calendar`
- `rca.weather`
- `rca.goals`
- `rca.signals`
- `rca.outcomes`
- `rca.events`
- `rca.completions`
- `rca.memory`
- `rca.evidence_cache`
- `rca.external_events`

## The Dashboard

The UI is a Next.js App Router app in `dashboard/`. It reads from the `rca` schema with the anon key and RLS.

- `/` -> Fleet Overview with a city/date heatmap and drop/lift badges.
- `/cities/[cityId]` -> City timeline of actual sales versus synthetic business goal with clickable signal markers.
- `/cities/[cityId]/rca` -> RCA history with decision card, RCA, prediction, and prescription.
- `/cities/[cityId]/logs` -> Run logs and completion records.
- `/cities/[cityId]/profile` -> Distilled memory notes.

## Skills

- **Project runtime skills** live in `rca/agent_skills/` and are loaded by the Python app during `rca run`.
- **Claude local skills** in `.claude/skills/` are assistant-side helpers and are not part of the deployed runtime.

## Out Of Scope

- Product/category drilldown.
- Store drilldown.
- Customer analysis.
