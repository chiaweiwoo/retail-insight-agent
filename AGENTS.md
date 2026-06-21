# AGENTS.md

Working notes and guardrails for the v2 RCA agent system.

## Guardrails

- Calibration matters more than eloquence.
- Every node must change the output in a visible way.
- Claims must stay tied to evidence we actually have.
- Margin is a risk lens here, not a computed metric.
- External evidence is supportive unless it clearly aligns with internal facts.
- The agent is allowed to say "unknown" when evidence is insufficient.
- Product/store-level conclusions are not allowed unless framed as follow-up data needs.

## Data Scale Limitations

- **Dataset**: `FreshRetailNet-50K` heavily normalizes sales figures.
- **Runtime Grain**: All runtime evidence is city/date only.
- **Cross-city caution**: Peer-style comparisons across cities are weak priors, not strong proof.
- **Source of truth**: Supabase is the sole runtime system of record. DuckDB is gone from runtime entirely.
- **Scope rule**: Product and store detail never survive into runtime tables. If the source contains store or product rows, we aggregate them into city/day facts such as counts, totals, rates, and intraday profiles.

## Public CLI

- `uv run python -m rca.cli build`
- `uv run python -m rca.cli signal`
- `uv run python -m rca.cli run --city <id> --date <YYYY-MM-DD>`
- `uv run python -m rca.cli mcp`

## Delivery Rule

- After meaningful code or documentation changes, commit and push them in small, readable commits instead of leaving the repo dirty.

## The LangGraph Pipeline

Orchestration is handled by LangGraph via `RcaState`. Graph: `START → investigation_loop → decision → evaluation → memory → record → END`.

The investigation loop is a bounded Python function (not a LangGraph subgraph) that runs up to `RCA_MAX_INVESTIGATION_ROUNDS` rounds:

1. **Planner**: Select agents, set objective, identify target gaps, list expected evidence.
2. **Specialists (Parallel)**: Run chosen internal agents in parallel via `ThreadPoolExecutor`. Evidence is accumulated into a typed ledger (one `observation` per tool call, one `inference` per memo).
3. **Critic**: Return a structured JSON review with `continue_investigation`, `gaps`, and `stop_reason`. Drives the loop stop decision.
4. **Loop stops when**: (a) critic says done, (b) all critic-identified gaps are `unavailable_data`, or (c) max rounds reached.

After the loop:

5. **Decision (Coordinator)**: Build a structured `DecisionBrief` JSON rendered into RCA, Prediction, and Prescription markdown sections.
6. **Evaluation**: Run 8 deterministic audit checks; compute a 0-to-1 quality score.
7. **Memory Distiller**: Extract reusable lessons and write them back to `rca.memory`.
8. **Record**: Persist outcomes, logs, completions, evidence ledger, and evaluation in Supabase.

## Tool Access

All tools read directly from Supabase `rca.*` tables.

| Agent | Tools |
| --- | --- |
| `statistician` | `get_signal_evidence`, `get_sales_context`, `compare_recent_baseline`, `compare_same_weekday_baseline`, `detect_intraday_shift`, `get_intraday_profile`, `run_stat_analysis` |
| `sales_agent` | `get_signal_evidence`, `get_sales_context` |
| `inventory_agent` | `get_inventory_context`, `get_intraday_profile`, `compare_recent_baseline` |
| `pricing_agent` | `get_pricing_context`, `get_signal_evidence` |
| `promotions_agent` | `get_promotions_context`, `get_signal_evidence` |
| `calendar_weather_agent` | `get_calendar_weather_context`, `get_signal_evidence` |
| `news_agent` | `search_external_events` (gated: requires internal evidence + `missing_external_context` critic gap + `RCA_RESEARCH_ENABLED=true`) |

`run_stat_analysis` requires non-empty `rationale` and `decision_use` fields before executing. Methods: `robust_baseline_check`, `driver_shift_scan`, `simple_expected_sales_sanity_check`. Gated by `RCA_STAT_TOOLS_ENABLED` (default true).

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

- `/` -> City signal heatmap with clickable city/date cells.
- `/cities/[cityId]` -> City timeline of actual sales versus synthetic business goal with clickable signal markers.
- `/cities/[cityId]/rca` -> RCA history with decision card, RCA, prediction, and prescription.
- `/cities/[cityId]/logs` -> Run logs and completion records.
- `/cities/[cityId]/profile` -> Distilled memory notes.

## Operational Notes

- `rca build` ingests stable city/date base tables from parquet.
- `rca signal` rebuilds the more experimental screening layer in `rca.signals`.
- `rca run` depends on `rca.signals`; run `build` and `signal` before running the LLM workflow on fresh data.
- For `rca.events`, `rca.completions`, and `rca.memory` inserts to work through the service role, `rca` schema sequences must be granted to `service_role`.

## Environment Variables

| Variable | Default | Effect |
| --- | --- | --- |
| `RCA_MAX_INVESTIGATION_ROUNDS` | `5` | Cap on investigation loop rounds |
| `RCA_RESEARCH_ENABLED` | `false` | Enable news agent and web search |
| `RCA_STAT_TOOLS_ENABLED` | `true` | Enable `run_stat_analysis` gated tool |
| `RCA_LLM_JUDGE_ENABLED` | `false` | Enable LLM quality judge in evaluation |

## Skills

- **Project runtime skills** live in `rca/agent_skills/` and are loaded by the Python app during `rca run`.
- **Claude local skills** in `.claude/skills/` are assistant-side helpers and are not part of the deployed runtime.

## Out Of Scope

- Product/category drilldown.
- Store drilldown.
- Customer analysis.
