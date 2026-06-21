# Agent System Technical Walkthrough

This document is a source-guided walkthrough of the Retail Insight Agent codebase.

It is meant to answer a very practical question:

> "If I open this repo cold, which files should I read first, what does each module own, and how does one RCA case move through the system?"

This document stays close to the code.

If you want the lighter mental model first, read `docs/AGENT_SYSTEM_OVERVIEW.md`.

If you want the conceptual design principles behind the system, read `docs/AGENT_SYSTEM_DESIGN.md`.

If you want the long teaching notes from beginner to advanced, read `docs/AGENT_SYSTEM_STUDY_NOTES.md`.

## Table of Contents

1. How to use this walkthrough
2. Start at the public CLI
3. Configuration and naming
4. Deterministic build flow
5. Signal materialization flow
6. Runtime orchestration in LangGraph
7. The bounded investigation loop
8. Planner mechanics
9. Specialist execution and tool calling
10. Critic mechanics
11. Decision brief synthesis
12. Deterministic evaluation
13. Memory writes and caches
14. Outcome and trace persistence
15. Simulation harness
16. Simulation reviewer
17. Dashboard routes for inspection
18. Suggested reading order by skill level
19. Best debugging paths
20. Final mental model

## How to use this walkthrough

Use this like an onboarding guide.

When a section says "Open this file," actually open it and skim while reading.

Recommended order:

1. `rca/cli.py`
2. `rca/config.py`
3. `rca/database.py`
4. `rca/graph.py`
5. `rca/agents.py`
6. `rca/tools.py`
7. `rca/state.py`
8. `rca/outcomes.py`
9. `rca/simulate.py`
10. `dashboard/src/app/...`

## 1. Start at the public CLI

Open this file:

- `rca/cli.py`

This is the best entrypoint because it tells you what the project treats as public behavior.

### Current public commands

```bash
uv run python -m rca.cli build
uv run python -m rca.cli signal
uv run python -m rca.cli run --city 0 --date 2024-06-09
uv run python -m rca.cli simulate --city 0
uv run python -m rca.cli mcp
```

### What each command maps to

| Command | Code path |
| --- | --- |
| `build` | `ingest_to_supabase()` in `rca/database.py` |
| `signal` | `materialize_signals_to_supabase()` in `rca/database.py` |
| `run` | `run_rca_graph()` in `rca/graph.py` |
| `simulate` | `simulate_city()` in `rca/simulate.py` |
| `mcp` | `mcp.run()` in `rca/mcp_server.py` |

### Why this matters

If you are ever unsure where some behavior starts, the CLI tells you which module owns it.

## 2. Configuration and naming

Open this file:

- `rca/config.py`

This file defines the vocabulary and runtime settings of the system.

### What lives here

- dataset boundaries
- table name constants
- environment variable readers
- sales semantics guardrails
- Supabase client helpers
- timestamp helpers

### What to pay attention to

#### Table constants

These keep the rest of the code from scattering raw table strings everywhere.

That matters because it makes schema-wide changes easier and reduces spelling bugs.

#### `SALES_FIELD_SEMANTICS`

This is a small constant with big importance.

It reminds the model that:

- `sale_amount` is normalized
- it is not currency
- it should not invent financial precision

#### Environment flags

Important runtime toggles include:

- `RCA_MAX_INVESTIGATION_ROUNDS`
- `RCA_RESEARCH_ENABLED`
- `RCA_STAT_TOOLS_ENABLED`
- `RCA_LLM_JUDGE_ENABLED`

These change runtime behavior directly, so they are often the first thing to inspect when the system behaves differently than expected.

## 3. Deterministic build flow

Open this file:

- `rca/database.py`

This file owns deterministic data preparation.

### Main idea

The build path aggregates raw rows into city/day facts that are small enough for runtime reasoning but rich enough to be useful.

### Functions worth reading in order

1. `load_scoped_raw_data()`
2. `build_sales_df()`
3. `build_inventory_df()`
4. `build_pricing_df()`
5. `build_promotions_df()`
6. `build_calendar_df()`
7. `build_weather_df()`
8. `build_goals_df()`
9. `ingest_to_supabase()`

### What each builder owns

| Builder | Output |
| --- | --- |
| `build_sales_df()` | city/day sales totals, counts, hourly sales |
| `build_inventory_df()` | city/day stockout counts and rates |
| `build_pricing_df()` | city/day discount summaries |
| `build_promotions_df()` | city/day activity summaries |
| `build_calendar_df()` | weekday, weekend, holiday-style context |
| `build_weather_df()` | city/day weather summaries |
| `build_goals_df()` | expected sales baseline |

### Why `build_goals_df()` matters

The goal table is upstream of both:

- the signal label
- the RCA story

If expected sales are poor, both signals and RCA will be noisy.

## 4. Signal materialization flow

Open these files:

- `rca/database.py`
- `rca/signals.py`

### Where signals are created

In `rca/database.py`, read:

- `build_signals_df()`
- `materialize_signals_to_supabase()`

This is the project's screening layer.

### What signal rows contain conceptually

- actual sales
- expected sales
- deviation percentage
- signal label
- signal strength
- baseline quality
- signal reason
- priority score
- first hypothesis hints

### Where signals are retrieved

In `rca/signals.py`, read:

- `get_signal_row()`
- `get_signal_dates_for_city()`

These are intentionally thin helpers.

That is good architecture:

- signal creation logic lives in one module
- signal retrieval logic stays simple

## 5. Runtime orchestration in LangGraph

Open this file:

- `rca/graph.py`

This file owns the outer runtime scaffold.

### Actual graph shape

```text
START
  -> investigation_loop
  -> decision
  -> evaluation
  -> memory
  -> record
  -> END
```

### Why the graph is this simple

The outer graph is meant to be easy to explain.

The more agentic behavior lives inside the `investigation_loop` node, which delegates to `run_investigation_loop()` in `rca/agents.py`.

### `RcaState`

Read the `TypedDict` carefully.

It tells you what the graph cares to preserve:

- identity: `city_id`, `dt`, `run_id`
- signal evidence
- investigation artifacts
- decision artifacts
- evaluation result
- memory note

### Node responsibilities

| Node | Responsibility |
| --- | --- |
| `investigation_loop_node()` | fetch signal + memory, run the bounded loop |
| `decision_node()` | create the final `DecisionBrief` and markdown fields |
| `evaluation_node()` | run deterministic audits |
| `memory_node()` | distill reusable lessons |
| `record_node()` | persist outcome and flush logs |

### `run_id`

`run_rca_graph()` creates a unique `run_id` per attempt:

```text
city_{city_id}_{dt}_{timestamp}
```

That means:

- `city_id` + `dt` identify the business case
- `run_id` identifies the specific attempt

That distinction is important for simulation batches, logs, and debugging.

## 6. The bounded investigation loop

Open this file:

- `rca/agents.py`

This is the core runtime module.

If you only deeply study one file, make it this one.

### Start with these definitions

- `AgentSpec`
- `AgentRunResult`
- `PlannerDecision`
- `AGENT_SPECS`

They define the runtime cast.

### What `run_investigation_loop()` does

Read it slowly.

For each round:

1. gather prior gaps and recent evidence summary
2. ask the planner what to do next
3. apply repetition guard
4. gate disallowed work such as premature news research
5. run selected specialists in parallel
6. convert tool calls and memos into evidence ledger items
7. ask the critic whether to continue
8. append a structured `InvestigationRound`
9. stop when the critic says enough, only unavailable gaps remain, or no new work exists

### Why this is the heart of the system

This loop is where the project becomes meaningfully agentic.

The system is no longer just:

```text
run tools once -> summarize once
```

It becomes:

```text
plan -> investigate -> critique -> replan if needed -> stop with a reason
```

## 7. Planner mechanics

Still in `rca/agents.py`, read:

- `plan_investigation()`

### Inputs to the planner

The planner receives:

- current signal evidence
- recent sales context
- calendar and weather context
- memory context
- prior critic gaps
- recent evidence summary
- current round number

### Outputs from the planner

It returns structured JSON parsed into `PlannerDecision`:

- `selected_agents`
- `rationale`
- `news_query`
- `objective`
- `target_gaps`
- `expected_evidence`

### Guardrails in code

Round 1 forces:

- `statistician`
- `sales_agent`

Research disabled means:

- `news_agent` is stripped out

If planner JSON parsing fails:

- there is a fallback agent set

That fallback is important. It keeps the harness from collapsing just because one planner response is malformed.

## 8. Specialist execution and tool calling

Still in `rca/agents.py`, read:

- `run_agent()`
- `_run_agents_parallel()`
- `agent_memo_to_evidence_items()`

### `run_agent()`

This function is the specialist execution engine.

It:

1. builds a role-specific system prompt
2. loads the matching skill file from `rca/agent_skills/`
3. gives the model only the tools that specialist is allowed to use
4. loops through tool-calling rounds
5. logs each tool call
6. records raw completion content to `rca.completions`

### Why bounded tools matter

Each specialist sees only its allowed tools.

That keeps:

- roles cleaner
- prompts smaller
- behavior easier to explain

### `news_agent` special case

If research is disabled, `news_agent` returns a bounded memo explaining that no external evidence was gathered.

That is a good example of policy being enforced in code, not merely suggested in prompt text.

### Evidence conversion

`agent_memo_to_evidence_items()` is an especially important function.

It turns:

- tool calls into `observation` evidence
- specialist memos into `inference` evidence

This gives later stages structured material to work with rather than a pile of markdown.

## 9. Critic mechanics

Still in `rca/agents.py`, read:

- `run_critic()`

### What the critic must decide

- whether the investigation should continue
- what the confidence ceiling should be
- what gaps remain
- which agents or tools are recommended next
- why the loop should stop if it stops

### Why the critic matters

Without the critic, the system would mostly be:

- gather some notes
- produce a summary

With the critic, the system can say:

- we still do not know enough
- we have enough evidence
- the only remaining gaps are unavailable

That is a big difference.

### Important distinction

The critic is **not** the evaluator.

The critic improves the current run.
The evaluator scores the finished run.

Keep that distinction sharp when you read the code.

## 10. Decision brief synthesis

Still in `rca/agents.py`, read:

- `run_decision_brief()`
- `_brief_to_markdown()`
- `extract_outcome_fields()`

### What happens here

The coordinator returns a structured `DecisionBrief`, not just loose prose.

Then the code renders that into markdown-compatible sections:

- Decision Card
- RCA
- Prediction
- Prescription

### What the coordinator is asked to produce

- headline
- confidence
- situation
- business impact
- most likely explanation
- evidence summary
- recommended action
- alternatives
- owner function
- urgency
- expected benefit
- monitoring plan
- unknowns
- caveats

### Why this is useful

It shifts the output from "interesting notes" toward "decision-ready artifact."

## 11. Deterministic evaluation

Open this file:

- `rca/audits.py`

This file owns deterministic post-run quality checks.

### What it checks conceptually

- unsupported scope leaps
- forbidden financial language
- empty evidence
- missing decision structure
- poor calibration
- missing monitoring plan

### Why deterministic audits are valuable

They catch obvious violations cheaply and repeatably.

That is important because LLM-only evaluation can drift.

In this project, deterministic evaluation is the first quality wall.

## 12. Memory writes and caches

Open this file:

- `rca/memory.py`

This file owns three related systems:

1. distilled lesson memory
2. evidence cache
3. external event cache

### Distilled memory

Read:

- `get_memory_notes()`
- `write_memory()`

This is the semantic lesson layer used across runs.

### Evidence cache

Read:

- `_cache_key()`
- `get_cached_evidence()`
- `put_cached_evidence()`

This is performance and repeatability memory.

### External event cache

Read:

- `get_cached_external_events()`
- `cache_external_events()`

This avoids redundant search behavior.

### Important insight

Together, these three systems are the practical version of "dynamic memory" in the repo.

## 13. Outcome and trace persistence

Open these files:

- `rca/outcomes.py`
- `rca/runlog.py`

### `rca/outcomes.py`

This file owns:

- `OutcomeRecord`
- `record_outcome()`
- `record_completion()`

Read `OutcomeRecord` carefully.

It shows the intended balance between:

- stable relational columns
- evolving JSON artifacts

### `rca/runlog.py`

This file owns the coarse-grained event log.

`RunLogger` buffers events and flushes them to `rca.events`.

This is one of the best first places to look when something feels wrong but you do not yet know whether the issue is:

- planner logic
- tool execution
- stop conditions
- persistence

## 14. Simulation harness

Open this file:

- `rca/simulate.py`

This module moves the system beyond one-off RCA demos.

### What `simulate_city()` does

1. resets existing outputs for a city
2. finds all triggered signal dates for that city
3. runs them oldest to latest
4. lets memory accumulate across the batch
5. reviews each output
6. writes review rows to `rca.simulate_review`
7. prints a batch summary

### Why chronology matters

The simulation harness is more meaningful because dates are processed oldest to latest.

That means later runs can benefit from:

- prior memory
- prior cached evidence
- prior cached external context

This makes simulation a useful study tool for "does the system learn over time?"

## 15. Simulation reviewer

Open this file:

- `rca/reviewer.py`

This module combines:

- deterministic evaluation
- LLM alignment review
- simulation review persistence

### Functions to study

- `review_outcome()`
- `store_simulate_review()`

### What gets stored

Each simulation review row includes conceptually:

- batch ID
- city/date
- eval score
- alignment score
- pros
- cons
- improvements
- reviewer comment
- deterministic checks

This is exactly the payload used by the simulation dashboard page.

## 16. Dashboard routes for inspection

Open these files:

- `dashboard/src/app/page.tsx`
- `dashboard/src/app/cities/[cityId]/page.tsx`
- `dashboard/src/app/cities/[cityId]/rca/page.tsx`
- `dashboard/src/app/cities/[cityId]/simulate/page.tsx`
- `dashboard/src/app/cities/[cityId]/logs/page.tsx`
- `dashboard/src/app/cities/[cityId]/profile/page.tsx`

### What each route is for

| Route | Role |
| --- | --- |
| `/` | city/date signal overview |
| `/cities/[cityId]` | actual vs goal timeline and signal markers |
| `/cities/[cityId]/rca` | RCA results for that city, optionally date-prioritized |
| `/cities/[cityId]/simulate` | simulation batch review results from `rca simulate` |
| `/cities/[cityId]/logs` | events and LLM completion traces |
| `/cities/[cityId]/profile` | memory notes |

### Why the simulation route matters

This route is the bridge between CLI simulation and dashboard inspection.

It lets you review:

- batch quality
- per-date failures
- reviewer feedback
- direct jump back to the RCA page

## 17. Suggested reading order by skill level

### If you are a beginner

Read:

1. `README.md`
2. `docs/AGENT_SYSTEM_OVERVIEW.md`
3. `docs/AGENT_SYSTEM_STUDY_NOTES.md`
4. `rca/cli.py`
5. `dashboard/src/app/...`

### If you are intermediate

Read:

1. `rca/cli.py`
2. `rca/graph.py`
3. `rca/agents.py`
4. `rca/tools.py`
5. `rca/outcomes.py`
6. `rca/simulate.py`

### If you are advanced

Read:

1. `rca/agents.py`
2. `rca/state.py`
3. `rca/tools.py`
4. `rca/audits.py`
5. `rca/reviewer.py`
6. `rca/memory.py`
7. `supabase/migrations/...`

## 18. Best debugging paths

### Case 1: the signal looks wrong

Open:

- `rca/database.py`
- `rca/signals.py`

Check:

- expected sales baseline
- signal thresholds
- label logic

### Case 2: the RCA sounds smart but ungrounded

Open:

- `rca/agents.py`
- `rca/tools.py`
- `rca/audits.py`

Check:

- evidence ledger size
- which tools were actually called
- whether the evaluator flagged any issue

### Case 3: simulation exists but quality is not improving

Open:

- `rca/simulate.py`
- `rca/reviewer.py`
- `rca/memory.py`

Check:

- whether memory is being written
- whether later runs are seeing that memory
- whether recurring cons are meaningful or generic

### Case 4: dashboard and backend disagree

Open:

- the relevant dashboard route
- `rca/outcomes.py`
- `rca/reviewer.py`

Check:

- table name
- selected columns
- sort order
- deployed branch

## 19. Final mental model

If you want one final sentence to remember the whole codebase:

This project is a city/date retail RCA harness where deterministic data prep feeds a bounded investigation loop, the loop writes structured evidence and decision artifacts into Supabase, simulation adds quality comparison across many runs, and the dashboard exists to help humans inspect and improve the system over time.
