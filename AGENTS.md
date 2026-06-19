# AGENTS.md

This document records agent architecture decisions and guardrails.
Source of truth for implementation is **README.md**.

## Architecture

Coordinator-led subagent design.

`plan_specialists(store_alias, dt, signal)` is the planning seam. It selects which specialist agents to dispatch for a given store-day. Currently returns all five specialists. Future filtering by signal direction or magnitude goes here — the seam isolates that logic.

Specialists run in parallel, each bounded to a named domain and a fixed set of tools. The coordinator synthesizes their memos into one RCA report. No specialist sees another specialist's memo.

| Specialist | Domain | Tools |
| --- | --- | --- |
| `sales_analyst` | Sales performance — confirm signal magnitude and trend | `get_signal_evidence`, `get_sales_context` |
| `ops_analyst` | Operations — stockout and availability | `get_stockout_context`, `get_sales_context` |
| `commercial_analyst` | Commercial — discount depth and promotional activity | `get_discount_context`, `get_activity_context`, `get_sales_context` |
| `market_analyst` | Market context — calendar, weather, peer stores | `get_calendar_weather_context`, `get_peer_store_context`, `get_sales_context` |
| `research_analyst` | External research — web news search for broader events | `search_news` |

Evidence is read-only over `data/rca.duckdb`. No writes to the DB during a run.

## Guardrails

- **One CLI entrypoint.** Everything runs through `rca <subcommand>`. No ad-hoc scripts.
- **Specialist tool access stays domain-bounded.** Each specialist is given only the tools it needs. The tool access matrix in README.md is the reference.
- **Planning seam stays isolated.** Changes to which specialists run for a given signal go into `plan_specialists()` only — not scattered through the coordinator or CLI.
- **Generated output is not committed.** Benchmark artifacts (`data/analysis/agent_benchmark_runs/`) and run logs (`data/runs.duckdb`) are gitignored.

## What Exists Now

- Vite/Evidence viewer app under `ui/` — serves `ui/public/evidence_data.json` and `ui/public/dashboard.html`
- Dashboard: `ui/public/dashboard.html` — signal grid + recent runs, rebuilt with `rca dashboard`
- Benchmark batch runner: `rca bench` over 6 fixed scenarios

## Still Out Of Scope

- MCP runtime
- Skills runtime
- Persistent memory
- Product/category drilldown
- Customer analysis
