# Agent System Technical Walkthrough

This document is a source-guided knowledge-transfer walkthrough for the Retail Insight Agent codebase.

The goal is simple:

- help you understand how the system works without reading every file cold
- walk the runtime path in the same order the code executes
- tell you which source file to open at each stage
- explain what each module owns
- explain what data goes in, what comes out, and what to inspect when debugging

This document is intentionally close to the code.

If you want a lighter introduction, read `docs/AGENT_SYSTEM_OVERVIEW.md`.

If you want more design philosophy and agent-system principles, read `docs/AGENT_SYSTEM_DESIGN.md`.

## How to use this document

Use this like an onboarding walkthrough.

Read the sections in order.

When a section says "Open this file", actually open it and scan the code while reading the explanation. That will make the system much easier to retain.

Recommended order:

1. CLI entrypoints
2. Build flow
3. Signal flow
4. Runtime graph
5. Investigation loop
6. Tools
7. State models
8. Outcomes, logs, memory, and evaluation
9. Replay and reviewer

## 1. Start at the CLI

Open this file:

- `rca/cli.py`

This is the best entrypoint because it tells you what the project considers public behavior.

At the time of writing, the CLI defines these commands:

- `build`
- `signal`
- `run`
- `mcp`
- `replay`

### What each command does

`build`

- calls `ingest_to_supabase()` from `rca/database.py`
- loads raw parquet
- aggregates to city/date tables
- resets and repopulates base runtime tables

`signal`

- calls `materialize_signals_to_supabase()` from `rca/database.py`
- reads base tables
- builds the screening layer in `rca.signals`

`run`

- calls `run_rca_graph()` from `rca/graph.py`
- this is the main RCA runtime path
- public CLI always uses the configured LLM; tests inject the stub client internally

`mcp`

- launches the MCP server so tools can be exposed to an external LLM interface

`replay`

- calls `replay_city()` from `rca/replay.py`
- reruns many signal dates for one city
- optionally resets prior outputs
- optionally reviews each run afterward

### Why this matters

The CLI file gives you the top-level shape of the system.

If you ever feel lost, come back here and ask:

- which path am I actually running
- which module owns that path

## 2. Configuration and vocabulary

Open this file:

- `rca/config.py`

This file defines the core vocabulary of the project.

### What lives here

- project paths
- dataset boundaries such as `DATE_START`, `DATE_END`, and `CITY_IDS`
- table names
- semantic guardrails such as `SALES_FIELD_SEMANTICS`
- default thresholds
- environment variables
- Supabase client creation

### Important things to notice

`SALES_FIELD_SEMANTICS`

- this tells the model that `sale_amount` is normalized, not currency
- this is one of the most important truth constraints in the whole project

Table name constants

- these are used throughout the code instead of hardcoding table strings
- when you inspect any data path, check which `TABLE_*` constant it uses

Environment variables

- `RCA_RESEARCH_ENABLED`
- `RCA_MAX_INVESTIGATION_ROUNDS`
- `RCA_STAT_TOOLS_ENABLED`

These affect runtime behavior directly.

### Debugging use

If behavior feels strange, always check config assumptions first:

- research unexpectedly off
- wrong model selection
- max rounds too low
- missing Supabase credentials

## 3. Build flow: parquet to city/date tables

Open this file:

- `rca/database.py`

This file owns the deterministic data preparation path.

It is one of the most important modules in the project because it defines what evidence the runtime is allowed to see.

### The build path in order

`load_scoped_raw_data()`

- loads the parquet file
- validates required columns
- validates hourly array lengths
- validates date range and city scope

This is the first place to inspect if the raw data itself is malformed.

`build_sales_df()`

- aggregates raw rows to one row per `city_id` + `dt`
- computes:
  - `total_sales`
  - `store_count`
  - `product_count`
  - `active_product_count`
  - `avg_sales_per_product`
  - hourly sales totals

Key idea:

- raw product/store rows still matter
- they are just collapsed into city/date facts

`build_inventory_df()`

- aggregates stockout-related information
- computes counts and rates
- also preserves hourly stockout rates

`build_pricing_df()`

- aggregates discount-related information

`build_promotions_df()`

- aggregates `activity_flag` into city/date features
- this is intentionally cautious because `activity_flag` is unlabeled

`build_calendar_df()`

- derives weekday, weekend, holiday flag, and inferred holiday name

`build_weather_df()`

- aggregates weather facts

`build_goals_df()`

- computes synthetic expected sales
- prefers:
  - `same_weekday_4w_avg_sales`
  - otherwise `recent_7d_avg_sales`

This is the source of the "expected sales" number used in signals and RCA.

### Reset behavior

Still in `rca/database.py`, inspect:

- `RESET_TABLES_FOR_BUILD`
- `reset_supabase_tables()`

This tells you exactly what gets deleted during a rebuild.

At the moment, `build` is destructive for runtime artifacts too, including:

- signals
- outcomes
- events
- completions
- memory
- evidence cache
- external events

That is acceptable at this learning stage, but it is an important behavior to know.

### Debugging use

If a runtime RCA looks wrong, ask first:

- is the base table actually wrong
- is the goal calculation wrong
- did `build` wipe the state I expected to preserve

## 4. Signal flow: decide where the system should pay attention

Open these files:

- `rca/database.py`
- `rca/signals.py`

The signal layer is the project’s screening layer.

Its job is not to do the RCA. Its job is to decide which city/date deserves RCA attention.

### Where signals are created

In `rca/database.py`, inspect:

- `build_signals_df()`

This function combines:

- `sales`
- `goals`
- `calendar`

And computes:

- `deviation_pct`
- `abs_deviation_pct`
- `signal_label`
- `signal_strength`
- `baseline_quality`
- `signal_reason`
- `priority_score`
- `first_hypothesis_hints`

### What the signal fields mean

`signal_label`

- `drop`
- `lift`
- `neutral`
- `insufficient_history`

`signal_strength`

- rough severity bucket based on absolute deviation

`baseline_quality`

- how trustworthy the baseline type is

`signal_reason`

- short plain-language explanation of why the row got that label

`priority_score`

- ranking aid for which rows are worth investigating first

`first_hypothesis_hints`

- machine-friendly hints for where the planner might start

### Where signals are read back

In `rca/signals.py`, inspect:

- `get_signal_row()`
- `get_signal_dates_for_city()`

These are intentionally thin helpers.

That is a good design choice:

- signal generation is in one place
- signal retrieval is in another

### Debugging use

If `rca run` seems to investigate the wrong date or wrong kind of event:

1. inspect `rca.signals`
2. inspect `build_signals_df()`
3. compare the expected sales baseline to the actual sales

## 5. Runtime orchestration starts in the graph

Open this file:

- `rca/graph.py`

This file is the runtime orchestrator.

The current graph is simpler than the full logical behavior because the bounded loop is hidden inside one node.

Graph shape:

```text
START
  -> investigation_loop
  -> decision
  -> evaluation
  -> memory
  -> record
  -> END
```

### Why the graph looks simple

The project deliberately keeps the outer flow explainable.

The complicated part, the bounded multi-round investigation, lives inside `run_investigation_loop()` in `rca/agents.py`.

That means:

- the graph remains easy to read
- the runtime still behaves agentically

### What `RcaState` contains

In `rca/graph.py`, inspect the `RcaState` `TypedDict`.

This is the graph-level state, not the deeper investigation state model.

It stores:

- identity: `city_id`, `dt`, `run_id`
- signal evidence
- investigation outputs
- decision output
- evaluation output
- memory output

### Node responsibilities

`investigation_loop_node()`

- fetches signal row
- fetches memory notes
- calls `run_investigation_loop()`
- converts typed state into JSON-serializable objects

`decision_node()`

- calls `run_decision_brief()`
- builds both structured JSON and markdown-compatible output

`evaluation_node()`

- calls `run_evaluation()` from `rca/audits.py`

`memory_node()`

- calls `run_memory_distiller()`

`record_node()`

- writes the final outcome to Supabase
- flushes the event log

### Important runtime detail

`run_id` in `run_rca_graph()` is currently built as:

- `"city_{city_id}_{dt}_{timestamp}"`

That means each run attempt gets a unique identifier.

If you are studying how reruns behave, inspect `run_id` plus `city_id`/`dt` together:
`city_id` and `dt` identify the business case, while `run_id` identifies the attempt.

## 6. The real brain is in `rca/agents.py`

Open this file:

- `rca/agents.py`

This is the most important file for understanding the runtime behavior.

It contains:

- agent definitions
- planner logic
- specialist execution
- evidence extraction
- critic logic
- bounded loop logic
- decision brief synthesis
- memory distillation

If you only study one file deeply, study this one.

## 7. Specialist definitions

Still in `rca/agents.py`, start at:

- `AgentSpec`
- `AgentRunResult`
- `PlannerDecision`
- `AGENT_SPECS`

### What `AGENT_SPECS` tells you

This is the runtime catalog of specialists.

Each agent has:

- a name
- a focus
- a bounded tool list
- a skill file

Current specialists:

- `statistician`
- `sales_agent`
- `inventory_agent`
- `pricing_agent`
- `promotions_agent`
- `calendar_weather_agent`
- `news_agent`

### What to notice

The `statistician` is not just a prose role.

It has access to:

- baseline comparison tools
- intraday shift detection
- `run_stat_analysis`

So this agent is the closest thing to a lightweight data scientist inside the loop.

## 8. How one specialist actually runs

Still in `rca/agents.py`, inspect:

- `run_agent()`

This function is the specialist execution engine.

### What it does

1. builds a system prompt from:
   - focus text
   - sales semantics
   - skill file

2. creates a short user prompt with city/date and focus

3. gives the model access only to that agent’s allowed tools

4. loops through model tool-calling rounds until:
   - the model stops calling tools
   - or it hits `DEFAULT_LLM_MAX_TOOL_ROUNDS`

5. logs every tool call

6. records the raw completion into `rca.completions`

### Why this matters

This is where "tool-using agent" becomes real.

The model is not just generating markdown. It is being forced through:

- bounded tool APIs
- repeatable tool schemas
- explicit completion logging

### Special case: `news_agent`

The function checks `RCA_RESEARCH_ENABLED`.

If research is disabled:

- it returns a memo explaining that no web research was performed

That is an example of policy being enforced in code, not left to prompt suggestion alone.

## 9. Evidence conversion

Still in `rca/agents.py`, inspect:

- `agent_memo_to_evidence_items()`

This function is important because it turns free-form agent work into typed evidence.

### What it does

For each agent result:

- one `observation` evidence item per tool call
- one `inference` evidence item for the memo itself

This is a useful pattern.

Instead of treating the entire memo as the only artifact, the system separates:

- what was retrieved
- what was interpreted

That gives the later critic and evaluator much better material to work with.

## 10. The planner

Still in `rca/agents.py`, inspect:

- `plan_investigation()`

This is the round planner.

### Inputs

It reads:

- signal evidence
- recent sales context
- calendar/weather context
- memory context
- prior critic gaps
- prior evidence summary
- current round number

### Outputs

It returns a `PlannerDecision` with:

- `selected_agents`
- `rationale`
- `news_query`
- `objective`
- `target_gaps`
- `expected_evidence`

### Important rules baked into code

Round 1:

- always includes `statistician`
- always includes `sales_agent`

Research disabled:

- strips `news_agent`

Fallback mode:

- if JSON parsing fails, the planner falls back to a predefined set of agents

### What to study in the source

Look at how the prompt is built differently for:

- first round
- later rounds with critic gaps

That is where the system starts behaving less like a static workflow and more like an investigation loop.

## 11. Parallel specialist execution

Still in `rca/agents.py`, inspect:

- `_run_agents_parallel()`

This function uses `ThreadPoolExecutor` to run selected specialists in parallel.

That means a single investigation round can fan out across multiple perspectives without serially blocking on each one.

### Why this matters

Parallelism here is a harness decision, not a model decision.

The system designer chose:

- planner decides which specialists matter
- harness runs them concurrently

That is a good example of hybrid design:

- model chooses
- code orchestrates

## 12. The critic

Still in `rca/agents.py`, inspect:

- `run_critic()`

This function turns specialist outputs plus recent evidence into a structured `CriticReview`.

### Critic responsibilities

It must answer:

- continue or stop
- what confidence ceiling is justified
- what gaps remain
- which agents/tools are recommended next
- why the loop should stop if it stops

### Why the critic is important

Without this layer, the system would be mostly:

- run some agents
- summarize whatever came back

With the critic, the system can say:

- this is still weak
- we need more evidence
- the next round should target these missing pieces

That is the core of the bounded agentic loop.

## 13. The bounded investigation loop

Still in `rca/agents.py`, inspect:

- `run_investigation_loop()`

This is the heart of the runtime.

Read this function slowly.

### What it does in plain language

For each round up to `RCA_MAX_INVESTIGATION_ROUNDS`:

1. collect prior gaps and recent evidence summary
2. ask the planner what to do next
3. apply repetition guard
4. gate `news_agent` if external investigation is not yet justified
5. run chosen agents in parallel
6. convert their outputs into evidence ledger items
7. ask the critic whether to continue
8. append an `InvestigationRound`
9. stop if the critic says enough, only unavailable gaps remain, or no new useful work remains

### Repetition guard

Study:

- `_make_investigation_key()`
- `used_keys`

The goal is to avoid dispatching the same agent for the same reason repeatedly.

This is one of those small but very important control mechanisms that make an agentic system feel disciplined instead of noisy.

### News gating

Look at the logic that decides whether `news_agent` survives filtering.

It requires:

- research enabled
- internal evidence already collected
- a critic gap of type `missing_external_context`

This is a strong example of policy gating in the harness.

## 14. Structured runtime state

Open this file:

- `rca/state.py`

This file defines the typed runtime state used inside the bounded loop.

### What to focus on

Read these models in order:

- `EvidenceItem`
- `Claim`
- `Hypothesis`
- `CriticGap`
- `CriticReview`
- `InvestigationRound`
- `MonitoringPlan`
- `DecisionBrief`
- `EvaluationResult`
- `MemoryInfluence`
- `RcaRunState`

### Why this file matters

This file tells you what the system believes are first-class concepts.

That is a very useful way to understand a codebase.

If something has a model here, the system is saying:

- this concept matters enough to structure
- this concept should survive beyond one prompt

### Important detail

`RcaRunState` has deterministic ID generators:

- `next_evidence_id()`
- `next_claim_id()`
- `next_hypothesis_id()`

This is useful because it makes evidence and claims traceable inside one run.

## 15. Decision brief synthesis

Go back to:

- `rca/agents.py`

Inspect:

- `run_decision_brief()`
- `_brief_to_markdown()`
- `extract_outcome_fields()`

### What happens here

The coordinator is no longer just returning loose markdown.

It is asked to return structured JSON for a `DecisionBrief`, then the code renders markdown-compatible sections from that object.

### What the brief includes

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

### Why this matters

This is where the system shifts from "analyst notes" toward "decision-ready output."

### Guardrails here

The coordinator prompt explicitly tells the model:

- no product/store root cause
- no dollar, revenue, or profit claims
- unknown is allowed
- external evidence is supportive only

When studying an agentic system, always look for where key truth constraints are enforced:

- prompt
- code
- evaluator

This project uses all three.

## 16. Evaluation layer

Open this file:

- `rca/audits.py`

This file implements the deterministic evaluator.

### What it does

It runs a set of rule-based checks against:

- the final decision brief
- the evidence ledger

### Checks currently implemented

- no currency terms
- no product/store root cause
- evidence ledger non-empty
- headline non-empty
- confidence calibration
- unknowns when evidence is thin
- external evidence not sole source
- monitoring plan populated

### Why this matters

This is not the critic.

This is the post-run quality gate.

That distinction is important:

- critic improves this run
- evaluator measures whether this run meets project standards

### What to study in the code

Look at:

- regex-based hard guards
- weighted scoring logic
- how `EvaluationResult` is built

This file is a very good example of how to keep agent quality grounded without relying only on another LLM.

## 17. Outcomes and persistence

Open this file:

- `rca/outcomes.py`

This file owns outcome persistence.

### What `OutcomeRecord` contains

Stable columns:

- `run_id`
- `city_id`
- `dt`
- `signal_label`
- `confidence`
- `headline`
- `status`
- `round_count`

Markdown compatibility columns:

- `decision_card_markdown`
- `report_markdown`
- `prediction_markdown`
- `prescription_markdown`

Structured JSON columns:

- `decision_brief_json`
- `hypotheses_json`
- `evidence_ledger_json`
- `investigation_rounds_json`
- `critic_reviews_json`
- `monitoring_plan_json`
- `evaluation_json`
- `memory_context_json`

### Why this is a good design

It mixes:

- stable relational fields for querying
- JSON artifacts for evolving agent structures

That is exactly the right tradeoff for a learning-stage agent system.

### Also inspect

- `get_prior_outcomes()`
- `get_latest_outcome_for_date()`
- `record_completion()`

These are important because they support:

- memory retrieval
- dashboard history
- LLM trace persistence

## 18. Event logging

Open this file:

- `rca/runlog.py`

This is the coarse-grained execution trace.

### What `RunLogger` does

- collects in-memory event rows
- assigns sequence numbers
- flushes them to `rca.events`

Each event records:

- actor type
- actor name
- action
- source
- details

### How to use this when debugging

If you want to know:

- which round stopped
- whether a tool ran
- whether the planner completed
- whether repetition guard blocked progress

Start here before diving into raw completions.

## 19. Memory and caching

Open this file:

- `rca/memory.py`

This file owns three related systems:

- distilled memory
- evidence cache
- external event cache

### Distilled memory

Inspect:

- `get_memory_notes()`
- `write_memory()`

This is the durable lesson layer.

### Evidence cache

Inspect:

- `_cache_key()`
- `get_cached_evidence()`
- `put_cached_evidence()`

This is used by tools such as:

- `compare_recent_baseline()`
- `compare_same_weekday_baseline()`
- `detect_intraday_shift()`

The cache key includes:

- tool name
- params
- build version

That is a good design because caches are tied to the current ingested data state.

### External event cache

Inspect:

- `get_cached_external_events()`
- `cache_external_events()`

This avoids repeated web searches for the same city/date/query.

## 20. Runtime tools

Open this file:

- `rca/tools.py`

This file is the runtime evidence API for the agent.

### Read it in this order

1. `_fetch_one()`
2. `_fetch_city_history()`
3. simple retrieval tools
4. derived comparison tools
5. external search tool
6. `run_stat_analysis()`
7. `TOOL_REGISTRY`
8. `execute_tool()`

### Simple retrieval tools

- `get_signal_evidence()`
- `get_sales_context()`
- `get_inventory_context()`
- `get_pricing_context()`
- `get_promotions_context()`
- `get_calendar_weather_context()`
- `get_intraday_profile()`

These mostly wrap table reads and convert them into model-friendly JSON.

### Derived tools

- `compare_recent_baseline()`
- `compare_same_weekday_baseline()`
- `detect_intraday_shift()`

These add runtime computation on top of raw facts.

This is where the project lets the agent do some real analytical work during execution rather than precomputing everything in ETL.

### External search

Inspect:

- `search_external_events()`

This uses DuckDuckGo search, then caches the results into `rca.external_events`.

### Gated stat tool

Inspect:

- `run_stat_analysis()`

This is an important advanced pattern.

The tool requires:

- `method`
- `rationale`
- `decision_use`

So the model must explain why the analysis is needed before it gets access to it.

That is a strong harness design choice.

### Tool registry

Inspect:

- `TOOL_REGISTRY`
- `get_tool_schemas()`
- `execute_tool()`

This is the final translation layer between:

- Python functions
- JSON schemas
- LLM function calling

## 21. Memory distillation

Go back to:

- `rca/agents.py`

Inspect:

- `run_memory_distiller()`

This function:

- asks the LLM for reusable lessons
- parses bullet lines
- stores both markdown and structured `memory_json`
- writes to `rca.memory`

### What to notice

The system does not treat "memory" as magic.

It treats it as:

- a short distilled lesson
- plus metadata
- stored in normal tables

That is a practical and teachable memory pattern.

## 22. Replay harness

Open this file:

- `rca/replay.py`

This is a new and important learning module.

It moves the system beyond one-off RCA runs.

### What replay does

1. optionally resets all prior outputs for a city
2. finds all triggered signal dates for that city
3. reruns them oldest to latest
4. lets memory accumulate across the batch
5. optionally reviews each run afterward

### Why this matters

This is the closest thing in the project to "learning over time" behavior.

It lets you answer questions like:

- does memory improve later dates
- do outputs stay aligned across many runs
- where does the system repeatedly fail

### Key functions

- `reset_city_state()`
- `find_signal_dates()`
- `replay_city()`

Study `replay_city()` closely if you want to understand how the project may evolve from single-run to batch-learning workflows.

## 23. Replay reviewer

Open this file:

- `rca/reviewer.py`

This module combines:

- deterministic evaluation from `rca/audits.py`
- LLM alignment review
- persistent review storage

### What it does

`review_outcome()`

- runs deterministic evaluation
- then asks a reviewer LLM to score alignment against project guardrails

`store_replay_review()`

- writes the review result to Supabase

### Why this matters

This is a second quality layer.

The main runtime evaluator is strict and deterministic.

The replay reviewer is more reflective and comparative.

That makes replay useful not just for rerunning dates, but for studying output quality across many runs.

## 24. Skill files and prompts

Open this folder:

- `rca/agent_skills/`

These markdown files are part of the agent behavior surface.

They are not source code, but they absolutely are runtime logic.

At minimum, open:

- `planner.md`
- `critic.md`
- `coordinator.md`
- `memory_distiller.md`
- a couple of specialist files such as `sales.md` and `statistician.md`

### Why this matters

If a module seems logically correct but the output quality is poor, the issue may live more in the skill files than in Python code.

## 25. One full `rca run` trace

Here is the full mental trace for one standard run:

1. CLI receives `rca run --city X --date Y`
2. `rca/cli.py` calls `run_rca_graph()`
3. `rca/graph.py` builds graph state and logger
4. `investigation_loop_node()` fetches:
   - signal row
   - recent memory notes
5. `run_investigation_loop()` starts round 1
6. planner selects agents
7. harness filters repeated or disallowed actions
8. selected specialists run in parallel
9. each specialist may call tools
10. tool results and memos become `EvidenceItem`s
11. critic reviews round results
12. if needed, round 2+ repeats
13. once loop stops, coordinator builds `DecisionBrief`
14. evaluator runs deterministic checks
15. memory distiller writes lessons
16. outcome is persisted to `rca.outcomes`
17. event log flushes to `rca.events`
18. CLI prints the final markdown decision card

If you can hold that sequence in your head, you understand most of the system.

## 26. Best debugging paths

If the output is wrong, debug in this order.

### Case 1: Wrong sales or baseline numbers

Open:

- `rca/database.py`
- `rca/tools.py`

Check:

- `build_goals_df()`
- `build_signals_df()`
- `get_signal_evidence()`
- `compare_same_weekday_baseline()`

### Case 2: Wrong city/date investigated

Open:

- `rca/signals.py`
- `rca/database.py`
- `rca/cli.py`

Check:

- signal row presence
- signal labels
- CLI input path

### Case 3: Agent seems repetitive or shallow

Open:

- `rca/agents.py`

Check:

- `plan_investigation()`
- `_make_investigation_key()`
- `run_investigation_loop()`
- `run_critic()`

### Case 4: Final answer sounds smart but is ungrounded

Open:

- `rca/agents.py`
- `rca/audits.py`
- `rca/agent_skills/coordinator.md`
- `rca/agent_skills/critic.md`

Check:

- evidence ledger size
- confidence calibration
- currency and scope checks
- whether unknowns were preserved

### Case 5: Memory is not helping

Open:

- `rca/memory.py`
- `rca/agents.py`
- `rca/state.py`
- `rca/replay.py`

Check:

- whether memory is being written
- whether planner receives memory
- whether `MemoryInfluence` records a meaningful effect
- whether replay actually lets memory accumulate across dates

## 27. Current design limitations

This walkthrough should also be honest about what the code does not yet do well.

Current limitations include:

- `run_id` is unique per attempt, but replay comparison still depends on `batch_id` discipline
- memory influence is recorded, but still fairly shallow
- hypotheses and claims are modeled in `rca/state.py`, but the current loop uses evidence much more heavily than explicit hypothesis tracking
- some persistence helpers still swallow exceptions silently
- replay and reviewer are newer layers and will likely evolve further

These are not failures. They are useful things to know when reading the code.

## 28. What to read next

If you want to go deeper after this walkthrough:

1. Re-read `rca/agents.py` end to end.
2. Re-read `rca/tools.py` and imagine which tool each agent is likely to use first.
3. Read `rca/state.py` and ask which types are already used fully versus only partially.
4. Run the graph integration test with the injected stub client and inspect:
   - `rca.outcomes`
   - `rca.events`
   - `rca.completions`
5. Run `replay` for one city and inspect whether later runs look better or just different.

That sequence will teach you more than jumping randomly between files.

## 29. Final mental model

If you want one sentence to remember the whole system:

This project is a city/date retail RCA harness where deterministic data prep feeds a bounded multi-agent investigation loop, which writes structured evidence, decision, evaluation, memory, and replay-review artifacts back into Supabase so humans can inspect and improve the system over time.
