# Agent System Overview

This document is the newcomer-friendly overview for the agent system in this project.

It is written for readers who want a clear explanation of:

- what this project is
- why we are building it
- what assets and components exist
- how the main flow works
- what the important boundaries are

This is not the deep technical design guide.

If you want the more advanced design material about how to build a strong agentic system, read `docs/AGENT_SYSTEM_DESIGN.md`.

## Table of Contents

1. What this project is
2. Why we are building it
3. Big picture architecture
4. What data and assets we have
5. Why the system uses city/date grain
6. Why `build`, `signal`, `run`, and `replay` are split
7. What the main agents do
8. What Supabase stores
9. What the dashboard shows
10. What is intentionally out of scope
11. How to inspect and debug the system
12. Key ideas to remember

## What this project is

This project is not a production retail analytics platform.

It is a learning sandbox for building a small but real autonomous agent system for retail root cause analysis.

The project is meant to feel closer to a small analyst-agent harness than to a static dashboard or a production-grade BI system.

## Why we are building it

The main learning goals are:

- how to turn rawer business data into an agent workflow
- how to separate ingestion, screening, reasoning, memory, evaluation, and presentation
- how to let the LLM do meaningful work at runtime instead of hiding everything in ETL
- how to inspect what the agent did after a run
- how to compare batches of runs and see whether the system is improving
- how to keep the system small enough to understand end to end

This project is designed to teach agent engineering, not just app building.

## Big picture architecture

At a high level, the project has five layers:

1. Data ingestion layer
2. Signal generation layer
3. LLM runtime layer
4. Replay and quality-review layer
5. Dashboard and inspection layer

The flow is:

```text
parquet
  ->
rca build
  ->
base tables in Supabase
  ->
rca signal
  ->
signal table in Supabase
  ->
rca run --city --date
  ->
agent workflow + tools + memory
  ->
outcomes / logs / completions / memory
  ->
rca replay --city
  ->
replay_review rows + batch summary
  ->
dashboard
```

This split matters because it keeps each layer understandable:

- `build` prepares stable facts
- `signal` chooses where attention should go
- `run` explains what happened for one city/date
- `replay` compares many runs and helps us study learning behavior

## What data and assets we have

The main assets in this project are:

- raw parquet data in `data/raw/`
- Python runtime code in `rca/`
- Supabase tables in schema `rca`
- runtime skill cards in `rca/agent_skills/`
- dashboard code in `dashboard/`
- documentation and ADRs in `docs/`

There are two broad classes of assets:

- stable assets such as raw data, base tables, and CLI commands
- experimental assets such as signal rules, prompts, memory, replay review, and agent behavior

That split is important because not every part of an AI system should change at the same speed.

## Why the system uses city/date grain

The runtime grain is city/date only.

That means the live agent reasons over evidence such as:

- total sales for a city/day
- expected sales for that city/day
- hourly sales shape
- stockout rates
- discount and activity summaries
- calendar and weather context

We intentionally do not expose product-level or store-level runtime tools.

### Why this constraint exists

If full product/store detail is kept inside the live agent loop:

- prompt context becomes too large
- tools become too granular
- the dashboard turns into a drilldown app
- the agent spends effort navigating detail instead of reasoning

By forcing city/date grain:

- the database stays compact
- the tools stay interpretable
- the dashboard stays simple
- the agent still has real work to do

### What happens to raw product/store data

It is not thrown away.

It is aggregated into city/date evidence such as:

- `store_count`
- `product_count`
- `active_product_count`
- `stockout_product_count`
- hourly sales totals
- hourly stockout rates

So product/store data still influences the runtime, just not as first-class runtime entities.

## Why `build`, `signal`, `run`, and `replay` are split

This is one of the most important design choices in the project.

### `rca build`

Purpose:

- stable ingestion
- deterministic transformation
- parquet to Supabase base tables

What it should feel like:

- reliable
- boring
- easy to rerun
- low conceptual risk

### `rca signal`

Purpose:

- create the screening layer that tells us which city/date is interesting enough to inspect

What it should feel like:

- tunable
- debatable
- changeable without rebuilding everything

### `rca run`

Purpose:

- use the signal and base evidence to run the LLM workflow for one city/date

Outputs:

- `rca.outcomes`
- `rca.events`
- `rca.completions`
- `rca.memory`
- sometimes `rca.evidence_cache`
- sometimes `rca.external_events`

### `rca replay`

Purpose:

- rerun every triggered date for one city
- let memory accumulate over time
- evaluate how stable or helpful the system is across many dates

Outputs:

- `rca.replay_review`
- printed batch summaries
- comparative learning signals for later debugging

This separation gives the project a clean mental model:

- build prepares facts
- signal chooses where to look
- run explains what happened
- replay tells us whether the system is getting better

## What the main agents do

The system is built around a small set of agents, each with a narrow role.

### Planner

Chooses which agents to run for a city/date and which gaps matter next.

### Statistician

Checks descriptive baselines, same-weekday comparisons, and intraday shifts.

### Sales agent

Focuses on the sales movement itself.

### Inventory agent

Looks at stockout and availability pressure.

### Pricing agent

Looks at discount behavior and pricing pressure.

### Promotions agent

Looks at `activity_flag`, but cautiously because it is unlabeled.

### Calendar/weather agent

Looks at weekday, inferred holiday, and weather context.

### News agent

Looks for external factors if research is enabled and the loop has a real external-context gap.

### Critic

Reviews specialist output and downgrades weak or overconfident claims.

### Coordinator

Synthesizes the investigation into the final business-facing answer.

### Memory distiller

Extracts reusable lessons from a completed run.

### Replay reviewer

Scores replayed outputs after the fact so we can compare batches and recurring weaknesses.

## What Supabase stores

The runtime system of record is Supabase under schema `rca`.

Base evidence tables:

- `sales`
- `inventory`
- `pricing`
- `promotions`
- `calendar`
- `weather`
- `goals`

Screening table:

- `signals`

LLM runtime tables:

- `outcomes`
- `events`
- `completions`
- `memory`
- `evidence_cache`
- `external_events`
- `replay_review`

Supabase matters here because it gives us one place to inspect both data facts and agent traces.

## What the dashboard shows

The dashboard is intentionally simple.

It is not meant to be a full enterprise BI suite. It is meant to help us inspect the system.

### Home page

Shows the city signal heatmap.

Its job is to answer:

- which city/date is interesting
- which signal is a drop or lift
- where to click next

### City page

Shows actual sales versus the synthetic business goal through time.

### RCA page

Shows the final business-facing explanation.

### Replay page

Shows the batch-level output of `rca replay`:

- which dates were replayed
- average evaluator and alignment scores
- reviewer pros, cons, and improvements
- deterministic checks per replayed date

### Logs page

Shows workflow events, completions, and tool-call traces.

### Memory page

Shows distilled lessons from prior runs.

## What is intentionally out of scope

This design is not trying to do everything.

Out of scope for now:

- product/category drilldown
- store drilldown
- customer analysis
- automated scheduling
- direct business automation such as changing price or inventory

That is deliberate. Strong boundaries make the system easier to learn from.

## How to inspect and debug the system

When something looks wrong, debug by layer.

### 1. Check ingestion

Run:

```bash
uv run python -m rca.cli build
```

Then inspect base tables such as `sales`, `inventory`, `pricing`, `promotions`, `calendar`, `weather`, and `goals`.

### 2. Check signal generation

Run:

```bash
uv run python -m rca.cli signal
```

Then inspect `rca.signals`.

Questions to ask:

- are row counts correct
- are drop/lift counts plausible
- is the city/date of interest present

### 3. Check run execution

Run:

```bash
uv run python -m rca.cli run --city 0 --date 2024-06-09
```

Then inspect:

- `rca.outcomes`
- `rca.events`
- `rca.completions`
- `rca.memory`

### 4. Check replay review

Run:

```bash
uv run python -m rca.cli replay --city 0
```

Then inspect:

- `rca.replay_review`
- the printed batch summary
- whether later dates seem to benefit from prior memory

### 5. Check dashboard wiring

If backend data looks correct but the UI looks wrong:

- verify the dashboard is deployed from the correct branch
- verify the page is querying the correct table
- verify you are not looking at a stale deployment

### 6. Check permissions

If writes silently disappear:

- check schema exposure
- check RLS
- check table grants
- check sequence grants for `bigserial` tables

## Key ideas to remember

If you only remember a few things from this project, remember these:

- separate stable layers from experimental layers
- let the LLM do real reasoning, but not all the work
- small, bounded agents are easier to trust than one vague super-agent
- memory is usually reusable state with policy
- replay plus review is how learning systems become inspectable over time
- logs and traces are part of the product when the goal is learning
- a simple dashboard can teach more than a fancy one
