# Retail Insight Agent v2 PRD

## Overview

Retail Insight Agent v2 is a learning-focused city/date retail RCA system.

It is designed to teach:

- LangGraph orchestration
- autonomous planning
- runtime tool use
- MCP
- memory
- critique
- internal versus external factor investigation
- retail decision framing

## Product Goal

The project should help a learner understand how to build an autonomous coding-agent-like workflow for retail analysis without hiding too much intelligence in ETL.

The system of record is Supabase. The dashboard is read-only. Runs are manual.

## Public Workflows

1. `rca build`
   Rebuilds the RCA evidence model from parquet.

2. `rca run --city <id> --date <YYYY-MM-DD>`
   Runs the LLM agent system for one city/date.

3. `rca mcp`
   Starts the MCP tool server for learning.

## Data Semantics

- `sale_amount` is normalized sales amount, not revenue.
- `activity_flag` is unlabeled.
- `holiday_flag` has no official holiday name in source data.
- product and store identifiers are aggregated away to city/date evidence.

## Evidence Model

All runtime evidence is city/date only.

Tables:

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

## Agent Model

The RCA harness separates:

- internal factors: database evidence
- external factors: web/news evidence

Agents:

- planner
- statistician/data scientist
- sales
- inventory
- pricing
- promotions
- calendar/weather
- news
- critic
- coordinator
- memory distiller

## Dashboard

Required dashboard capabilities:

- fleet heatmap of signals
- city timeline of actual sales versus synthetic business goal
- clickable signal markers
- RCA view with RCA, prediction, and prescription
- logs page
- memory page

## Constraints

- no scheduled jobs
- no product/store drilldown
- no heavy ETL statistics
- moderate tests only
- docs should be strong and beginner-friendly
