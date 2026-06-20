# Agent System Study Notes

## Table of Contents

1. What this project is for
2. Why city/date evidence only
3. Internal vs external factors
4. Why LangGraph
5. Runtime skills vs Claude skills
6. The agent lineup
7. Why a statistician agent matters
8. Why a news agent matters
9. Memory design
10. Signals and synthetic business goals
11. Retail concepts that shape decisions
12. MCP in this project
13. Dashboard reading guide
14. Common failure modes

## What this project is for

This project is not trying to be the perfect retail analytics stack. It is trying to be a clear learning environment for autonomous-agent engineering.

The design goal is:

- keep the data meaningful
- keep the workflows inspectable
- keep the dashboard small
- push more reasoning into the runtime

## Why city/date evidence only

The raw parquet has store and product identifiers, but v2 deliberately aggregates them away.

That gives us a clean learning constraint:

- the database stores facts at city/date grain
- the agent must reason from those facts
- the system avoids becoming a product drilldown app

Store and product values still contribute to city/date facts such as `store_count` and `product_count`.

## Internal vs external factors

Internal factors are everything we can read from Supabase:

- sales
- inventory
- pricing
- promotions
- calendar
- weather
- goals
- signals
- memory

External factors come from web search:

- public events
- local disruptions
- retail headlines
- macro context

This split is useful because it keeps the agent honest about evidence provenance.

## Why LangGraph

LangGraph already exists in the repo and is a good fit for:

- stateful orchestration
- planner -> workers -> critic -> coordinator flow
- bounded loops
- dynamic routing
- memory-aware execution

We do not need another dynamic graph library for v2.

## Runtime skills vs Claude skills

`.claude/skills` are developer-assistant helpers. They do not run in Vercel or Supabase.

`rca/agent_skills/*.md` are project-owned runtime instruction cards. The Python app loads them during `rca run`.

That makes skills part of the deployed project logic instead of only a local assistant feature.

## The agent lineup

- planner
- statistician/data scientist
- sales agent
- inventory agent
- pricing agent
- promotions agent
- calendar/weather agent
- news agent
- critic
- coordinator
- memory distiller

## Why a statistician agent matters

The statistician agent lets the runtime compute:

- recent baselines
- same-weekday baselines
- intraday shifts
- simple descriptive comparisons

This is exactly the kind of work that used to be baked into ETL, but now lives in the agent/tool layer.

## Why a news agent matters

Retail is not only internal.

Weather, public events, disruptions, holidays, and news can change demand. A news agent teaches:

- external evidence gathering
- cached search behavior
- how to blend weak external evidence with stronger internal facts

## Memory design

Memory is split into:

- `memory`: reusable lessons
- `evidence_cache`: computed tool outputs keyed by build version
- `external_events`: cached search results

This touches the main memory concepts without needing a dedicated memory framework.

## Signals and synthetic business goals

The dataset has no real corporate target. v2 therefore creates a synthetic expected-sales goal.

Use:

- same-weekday history when available
- recent rolling history as fallback

Signals are then:

- drop
- lift
- neutral
- insufficient_history

The LLM can challenge the signal later, but the dashboard needs a fast screening layer.

The operational split is deliberate:

- `rca build` creates stable base facts
- `rca signal` creates the more tunable screening layer
- `rca run` consumes the signal plus the raw city/date evidence

## Retail concepts that shape decisions

- realized sales are not always demand
- stockouts can cap sales
- intraday timing matters
- discounting can change sales and risk
- activity is unlabeled and must be handled cautiously
- holidays are inferred
- weather is context, not automatic proof
- external events may matter more than internal metrics on some days

## MCP in this project

`rca mcp` exposes the same evidence tools used by the agent runtime.

That makes this project a good MCP learning sandbox:

- tools are real
- domain is concrete
- outputs are inspectable in the dashboard

## Dashboard reading guide

Start with the heatmap.

Then:

1. open a city
2. inspect actual versus synthetic goal
3. click a signal marker
4. read the RCA result
5. inspect logs and completions
6. check the distilled memory

The Logs page also exposes:

- workflow events
- raw node completions
- tool call traces from `tool_calls_json`

## Common failure modes

- overclaiming from weak evidence
- treating activity as a labeled promotion
- treating inferred holidays as source truth
- mistaking descriptive statistics for causality
- stale cached evidence after rebuild
- overusing external search when internal evidence is already sufficient
