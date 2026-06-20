# ADR 0001: v2 Core Decisions

## Status

Accepted.

## Decision Summary

- Keep only three public CLIs: `build`, `run`, `mcp`.
- Use Supabase schema `rca`.
- Keep runtime evidence at city/date grain only.
- Aggregate away product and store detail.
- Use synthetic expected-sales goals for screening.
- Use `signals`, not `triggers`.
- Split RCA into internal and external factors.
- Include a news agent.
- Include a statistician/data scientist agent.
- Use LangGraph as the graph runtime.
- Use project-owned runtime Markdown skill cards.
- Use custom Supabase-backed memory and evidence cache.
- Drop Langfuse by default.
- Keep the dashboard simple and learning-oriented.

## Rationale

These decisions keep the project honest to its learning goal:

- enough structure to teach real agent design
- not so much precomputation that the agent has nothing meaningful to do
- not so much frontend or platform complexity that the core ideas get buried
