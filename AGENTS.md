# AGENTS.md

This document records agent architecture decisions and guardrails.
Source of truth for implementation is **README.md**.

## Architecture

Coordinator-led subagent design.

`plan_specialists(store_alias, dt, signal)` is the planning seam. It selects which specialist agents to dispatch for a given store-day. Currently returns all four specialists. Future filtering by signal direction or magnitude goes here — the seam isolates that logic.

Specialists run in parallel, each bounded to a named domain and a fixed set of tools. The coordinator synthesizes their memos into one RCA report. No specialist sees another specialist's memo.

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
- External news agent
- Product/category drilldown
- Customer analysis
