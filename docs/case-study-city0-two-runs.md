# Retail RCA Agent — Case Study: City 0, Two Holiday Signals

**System:** Retail Insight Agent v2  
**City:** 0 (highest sales volume in the 18-city sandbox, 290 stores, ~25 000 active products)  
**Runs:** 2024-05-01 Labour Day lift · 2024-06-09 Dragon Boat Festival drop  
**Generated:** 2026-06-21

---

## Table of Contents

1. [How the System Works — LangGraph Pipeline](#1-how-the-system-works--langgraph-pipeline)
2. [What Is Stored and Where](#2-what-is-stored-and-where)
3. [Case Study 1 — May 1, 2024: Labour Day Lift](#3-case-study-1--may-1-2024-labour-day-lift)
   - 3.1 [Signal Context](#31-signal-context)
   - 3.2 [Node: Planner](#32-node-planner)
   - 3.3 [Node: Specialist Agents (Parallel)](#33-node-specialist-agents-parallel)
   - 3.4 [Node: Critic](#34-node-critic)
   - 3.5 [Node: Decision Brief (Coordinator)](#35-node-decision-brief-coordinator)
   - 3.6 [Node: Evaluation](#36-node-evaluation)
   - 3.7 [Node: Alignment Reviewer (LLM Judge)](#37-node-alignment-reviewer-llm-judge)
   - 3.8 [Node: Memory Distiller](#38-node-memory-distiller)
   - 3.9 [Final Output Written to Database](#39-final-output-written-to-database)
4. [Case Study 2 — June 9, 2024: Dragon Boat Festival Drop](#4-case-study-2--june-9-2024-dragon-boat-festival-drop)
   - 4.1 [Signal Context](#41-signal-context)
   - 4.2 [Node: Planner](#42-node-planner)
   - 4.3 [Node: Specialist Agents (Parallel)](#43-node-specialist-agents-parallel)
   - 4.4 [Node: Critic](#44-node-critic)
   - 4.5 [Node: Decision Brief (Coordinator)](#45-node-decision-brief-coordinator)
   - 4.6 [Node: Evaluation](#46-node-evaluation)
   - 4.7 [Node: Alignment Reviewer (LLM Judge)](#47-node-alignment-reviewer-llm-judge)
   - 4.8 [Node: Memory Distiller](#48-node-memory-distiller)
   - 4.9 [Final Output Written to Database](#49-final-output-written-to-database)
5. [Cross-Run Comparison](#5-cross-run-comparison)
6. [Architecture and Production Design Review](#6-architecture-and-production-design-review)

---

## 1. How the System Works — LangGraph Pipeline

### What is LangGraph?

**LangGraph** is a graph execution library from LangChain. You define a **directed graph** where each **node** is a Python function and each **edge** is a directed transition between nodes. The runtime calls each node in order, passing a shared **state object** through the graph. Nodes can read from state, write back to it, and the next node picks up where the previous left off.

This system uses **LangGraph** to wire together the investigation pipeline in a single Python call: `run_rca_graph(city_id, dt)`. The graph is defined once at startup and reused for every run.

### Graph Topology

```
START
  │
  ▼
investigation_loop   ← bounded Python function (NOT a LangGraph subgraph)
  │                    internally runs: planner → specialists (parallel) → critic
  │                    repeats up to RCA_MAX_INVESTIGATION_ROUNDS times
  ▼
decision             ← coordinator synthesises DecisionBrief JSON
  │
  ▼
evaluation           ← deterministic 8-check audit + optional LLM alignment judge
  │
  ▼
memory               ← memory distiller writes lessons to rca.memory
  │
  ▼
record               ← persists everything to Supabase
  │
  ▼
END
```

### The Shared State Object (`RcaState`)

**LangGraph** passes a single Python dict (typed as `RcaState`) between every node. Each node receives the full dict and returns a partial dict with only the keys it changed. LangGraph merges those back in. This is why you never see explicit function-to-function argument passing — everything rides on state.

Key fields on state:

| Field | Type | Written by |
|---|---|---|
| `run_id` | str | `START` |
| `signal_evidence` | dict | `investigation_loop` |
| `evidence_ledger` | list | `investigation_loop` (appended per round) |
| `investigation_rounds` | list | `investigation_loop` |
| `critic_reviews` | list | `investigation_loop` |
| `decision_brief` | dict | `decision` node |
| `decision_card_markdown` | str | `decision` node |
| `final_report` | str | `decision` node |
| `evaluation` | dict | `evaluation` node |
| `memory_notes` | list | pre-loaded before `investigation_loop` |

### Model Routing

Not all nodes use the same LLM. The `NODE_MODEL_MAP` in `rca/llm.py` routes each node name to either `"fast"` (`deepseek-v4-flash`) or `"deep"` (`deepseek-v4-pro`):

| Node | Model tier | Reason |
|---|---|---|
| `planner` | fast | JSON selector — deterministic, cheap |
| `statistician` | fast | Tool-use loop, structured outputs |
| `sales_agent` | fast | Tool-use loop, structured outputs |
| `inventory_agent` | fast | Tool-use loop, structured outputs |
| `pricing_agent` | fast | Tool-use loop, structured outputs |
| `promotions_agent` | fast | Tool-use loop, structured outputs |
| `calendar_weather_agent` | fast | Tool-use loop, structured outputs |
| `news_agent` | fast | Web search, structured outputs |
| `critic` | fast | JSON reviewer |
| `coordinator` | **deep** | Final synthesis — nuance matters |
| `decision_brief` | **deep** | Same node as coordinator |
| `evaluation` | fast | Rule-based + LLM judge |
| `memory_distiller` | fast | Markdown extraction |
| `reviewer` | **deep** | LLM alignment judge — quality judgement |

---

## 2. What Is Stored and Where

Every `rca run` writes to **seven Supabase tables** in the `rca` schema. Here is what each one contains:

### `rca.outcomes` — The primary result record

One row per `run_id`. The most important table. Contains the final distilled output plus every intermediate JSON blob from the run. Column-by-column:

| Column | What it holds |
|---|---|
| `run_id` | e.g. `city_0_2024-05-01_20260621T172349_SGT` — unique per run |
| `city_id`, `dt` | The city and date investigated |
| `signal_label` | `"lift"` or `"drop"` |
| `confidence` | The coordinator's rated confidence: `"low"`, `"medium"`, or `"high"` |
| `headline` | One-sentence summary — what the agent decided happened |
| `status` | `"complete"` when the run finished without error |
| `round_count` | How many investigation rounds the loop ran (1 in both these runs) |
| `generated_at` | SGT timestamp of when the run completed |
| `decision_card_markdown` | The short Decision Card — headline + confidence + signal |
| `report_markdown` | The human-readable RCA narrative (situation + explanation) |
| `prediction_markdown` | What to watch next, review horizon, escalation trigger |
| `prescription_markdown` | Recommended action + alternatives |
| `decision_brief_json` | The full structured `DecisionBrief` object as JSON — all fields the coordinator produced |
| `evidence_ledger_json` | Every piece of evidence collected: one observation per tool call, one inference per agent memo |
| `investigation_rounds_json` | Per-round record: which agents ran, what evidence IDs were produced, critic review |
| `critic_reviews_json` | All critic JSON outputs from every round |
| `evaluation_json` | Deterministic check results + alignment judge scores |
| `monitoring_plan_json` | Structured monitoring plan from the coordinator |
| `hypotheses_json` | Placeholder for future hypothesis tracking (empty in current runs) |
| `memory_context_json` | Whether prior memory was used, and which memory IDs were loaded |

### `rca.events` — Workflow execution trace

One row per significant event during execution. This is the **workflow log** — not the business output. Columns:

| Column | What it holds |
|---|---|
| `run_id` | Links back to `outcomes` |
| `actor_type` | `"workflow"`, `"agent"`, or `"tool"` |
| `actor_name` | e.g. `"planner"`, `"statistician"`, `"get_signal_evidence"` |
| `action` | `"started"` or `"completed"` |
| `source` | `"system"` (deterministic) or `"llm"` (AI-generated) |
| `details` | JSON with context: which round, how many tool calls, etc. |
| `created_at` | Timestamp |

These rows let you replay the execution order and see which LLM calls happened when.

### `rca.completions` — Every raw LLM API response

One row per LLM call. The most granular data. Contains:

| Column | What it holds |
|---|---|
| `run_id` | Links back to `outcomes` |
| `node_name` | Which node made the call: `"planner"`, `"statistician"`, `"coordinator"`, etc. |
| `model` | Exact model ID used (e.g. `deepseek-v4-flash`) |
| `content` | The full text of what the LLM returned |
| `prompt_tokens` | Input token count |
| `completion_tokens` | Output token count |
| `tool_calls_json` | If the response included tool calls, the full list with arguments and results |
| `created_at` | Timestamp |

This table is the raw receipt for every API call.

### `rca.memory` — Distilled lessons for future runs

One row per run, containing the lessons the memory distiller extracted. Columns:

| Column | What it holds |
|---|---|
| `city_id`, `dt`, `run_id` | Provenance |
| `memory_type` | Always `"lesson"` currently |
| `topic` | `"rca_lesson"` |
| `content` | Markdown text of the lessons |
| `memory_json` | Structured `{ "lessons": [...], "version": 1 }` |
| `signal_label` | Whether this came from a drop or lift run |
| `influence_score` | Default `0.5` — how much weight future runs should give this memory |
| `created_at` | Timestamp |

The **planner** loads these rows at the start of each new run via `get_memory_context()` and passes them to the LLM as context, so the agent can learn from prior investigations.

### `rca.evidence_cache` — Cached tool results

One row per unique tool+arguments combination. Prevents duplicate Supabase queries during a run. The statistician and inventory agent sometimes call the same baseline function — the cache returns the stored result instead of re-querying.

### `rca.external_events` — Web search results

Populated when the `news_agent` fires. Each row holds one external search result. Empty in both these runs because the `news_agent` was not selected (no `missing_external_context` gap was serious enough to trigger it in round 1 and the critic stopped early).

### `rca.simulate_review` — Alignment judge output for batch comparison

Written when `review_outcome()` runs, either from within `rca simulate` or from the `evaluation_node` when `RCA_LLM_JUDGE_ENABLED=true`. Contains the deterministic checks + LLM alignment scores per run, making it the primary table for cross-batch quality comparison.

---

## 3. Case Study 1 — May 1, 2024: Labour Day Lift

**Run ID:** `city_0_2024-05-01_20260621T172349_SGT`  
**Signal:** `lift` · **Deviation:** `+26.2%` · **Confidence:** `high`

### 3.1 Signal Context

Before any LLM is called, the system reads from `rca.signals` to get the pre-computed signal row for this city/date. This row was built by `rca signal` (a deterministic pandas pipeline, no LLM involved).

**Signal row for city 0 on 2024-05-01:**

```
signal_label:          lift
goal_method:           same_weekday_4w      ← baseline: average of same weekday over prior 4 weeks
current_sales:         27,610
expected_sales:        21,874               ← 4-week Wednesday average
deviation_pct:         +26.2%               ← exceeds lift threshold of +25%
holiday_name_inferred: labor_day_period     ← inferred from date, not confirmed
weekday:               wednesday
signal_strength:       strong
priority_score:        41.22
```

The **threshold** that triggered the signal: `+25%` vs same-weekday-4w baseline. This is a purely mathematical check — no LLM is involved at this stage.

---

### 3.2 Node: Planner

**What the planner does:** Reads the signal, recent sales history, calendar/weather, and prior memory. Returns a JSON decision: which specialist agents to run, why, and what the investigation objective is.

**System prompt sent to the LLM:**

```
You are planning a city/date retail RCA investigation round. Return valid JSON only.
Allowed agents: statistician, sales_agent, inventory_agent, pricing_agent,
promotions_agent, calendar_weather_agent, news_agent.
Round 1: always include statistician and sales_agent.
External web research is enabled.
Return JSON: {selected_agents, rationale, news_query, objective,
target_gaps (list of gap IDs from prior critic review),
expected_evidence (list of strings)}
[+ planner.md skill file]
```

**User message (data payload):**

```json
{
  "city_id": 0,
  "dt": "2024-05-01",
  "round_index": 1,
  "signal": { "signal_label": "lift", "deviation_pct": 26.22, "holiday_name_inferred": "labor_day_period", ... },
  "sales": { "current_total_sales": 27610.34, "history": [...14 days...] },
  "calendar_weather": { "holiday_flag": true, "avg_temperature": 19.98, ... },
  "memory": []   ← no prior memory yet; this is the first run for city 0
}
```

**Planner's decision (what the LLM returned):**

The planner selected all six internal specialist agents: `statistician`, `sales_agent`, `inventory_agent`, `pricing_agent`, `promotions_agent`, `calendar_weather_agent`.

Rationale: broad first-round sweep because the signal is a holiday lift — every dimension (sales pattern, inventory capacity, discount depth, promotional activity, calendar effect) may contribute.

The `news_agent` was **not selected in round 1** — it can only fire in round 2+ after the critic identifies a `missing_external_context` gap and after at least one round of internal evidence exists.

> **Key design decision:** The planner is gated. `news_agent` cannot fire in round 1 even if selected. This prevents the model from going to web search before reading internal data — a common failure mode in LLM research agents.

---

### 3.3 Node: Specialist Agents (Parallel)

All six selected agents run simultaneously in a **`ThreadPoolExecutor`**. Each agent gets its own LLM conversation — completely independent, no shared context. The agents are:

#### Specialist agent system prompt template

Every specialist agent receives this base system prompt:

```
You are a retail RCA agent focused on {focus}.
sale_amount and hours_sale are normalized sales amounts from the source dataset.
Treat them as relative sales amounts for comparison, not currency and not literal units.
Use plain ASCII markdown. Distinguish observation from inference.
Return sections:
## Why It Matters
## Evidence
## Interpretation
## Caveats
[+ agent-specific skill file, e.g. statistician.md]
```

The user message is simply: `"Analyze city 0 on 2024-05-01. Focus: {focus}."`

Each agent then **calls tools** in a loop (up to `DEFAULT_LLM_MAX_TOOL_ROUNDS = 6` rounds) until it decides it has enough data and returns its memo without a tool call.

#### Tool call mechanism

When an agent calls a tool, the sequence is:
1. Agent sends a message with `tool_calls` in the response
2. System executes the Python function (e.g. `get_signal_evidence(city_id=0, dt="2024-05-01")`) — a Supabase query
3. Result is appended to the conversation as a `"tool"` role message
4. LLM receives the tool result and decides whether to call more tools or write its memo
5. When the LLM returns a message with no tool calls, the loop ends

Each tool call produces one **`observation`** entry in the evidence ledger. Each agent's final memo produces one **`inference`** entry.

---

#### `statistician` — Signal validation and statistical checks

**Focus:** Validate the signal with runtime baselines, intraday shape, and descriptive statistics.

**Tools called (in order):**
1. `get_signal_evidence` → confirms lift at +26.2%, `holiday_name_inferred: labor_day_period`
2. `get_sales_context` → 14-day history; today's 27,610 looks elevated vs recent days
3. `compare_recent_baseline` → vs 7-day rolling average: **+14.2%** (still a lift, but smaller)
4. `compare_same_weekday_baseline` → vs prior 4 Wednesdays: **+26.2%** (matches signal)
5. `get_intraday_profile` → hourly breakdown: peak at 09:00 (13.28% of daily sales) — **morning-heavy**
6. `detect_intraday_shift` → hours 8/9/10 share rose +2–3.5 ppts vs 7-day baseline; hour 15 fell -2 ppts
7. `run_stat_analysis` × 3:
   - `robust_baseline_check`: confirms the +26.2% is credible, not a baseline artefact
   - `driver_shift_scan`: morning shift is statistically notable
   - `simple_expected_sales_sanity_check`: deviation exceeds 10% → **material**

**Evidence items produced:** 9 observation items (`ev_001` to `ev_009`) + 1 inference (`ev_010`)

**Statistician's inference memo (excerpt):**
> "Validating the signal for city 0 on 2024-05-01 is important because the signal label is **"lift"** and the deviation (+26.2%) exceeds the 25% lift threshold. If this is a genuine lift, it may indicate a real demand increase (possibly related to the Labor Day period). If spurious, acting on it could lead to overstocking or misallocated resources... The lift is real and robust. It is not an artefact of the baseline method."

---

#### `sales_agent` — Sales movement explanation

**Focus:** Explain sales movement versus expected sales and recent history.

**Tools called:**
1. `get_signal_evidence` → same signal data as statistician (parallel, no cache benefit here)
2. `get_sales_context` → same 14-day history

**Evidence items produced:** 2 observations (`ev_011`, `ev_012`) + 1 inference (`ev_013`)

**Sales agent's inference (excerpt):**
> "Sales on **May 1st** came in at **27,610**, which is **26.2% above the expected level** of 21,874. This is a strong 'lift' signal — the system flagged it because it exceeded the 25% lift threshold. Understanding whether this is a genuine demand surge, a holiday effect, or a data anomaly matters for inventory planning, staffing, and promotional assessment."

---

#### `inventory_agent` — Stockout and availability pressure

**Focus:** Assess whether stockout or availability pressure likely contributed to the move.

**Tools called:**
1. `get_inventory_context` → **31.1% of products** had a stockout event during the day; avg stockout hours: 2.28; severe stockout rate: 13.6%
2. `get_intraday_profile` → same hourly data; stockout rates low during morning peak (3.5–8.5%) but rise through afternoon
3. `compare_recent_baseline` → +14.2% vs 7-day baseline

**Key finding:** Stockout rates were **low during the morning sales peak** (hours 6–10), meaning availability did not constrain the lift. Stockouts rose through the afternoon but by then the peak demand had already converted. The agent concluded: inventory was adequate and did not suppress the lift, but was not velocity-weighted — a caveat it correctly flagged.

---

#### `pricing_agent` — Discount depth and pricing pressure

**Focus:** Assess discount depth and pricing pressure.

**Tools called:**
1. `get_pricing_context` → avg discount: **0.921** (i.e. 7.9% off full price); discounted product rate: **50.7%**; deep discounted rate: **0%**
2. `get_signal_evidence` → signal context

**Key finding:** Broad but **shallow** discounting. Half the product range was discounted, but no product received a deep discount. This is the signature of a **holiday markdown** rather than a distress sale — the store supported demand without sacrificing margin. The pricing agent's inference correctly noted this means the lift was likely demand-driven, not discount-driven.

---

#### `promotions_agent` — Unlabeled activity indicator

**Focus:** Assess the unlabeled activity indicator and possible promotion contribution.

**Tools called:**
1. `get_promotions_context` → `activity_flag` products: **40.1% of products**, **39.5% of sales** came from flagged items; `activity_sales`: 10,891
2. `get_signal_evidence` → signal context

> **Critical nuance:** The `activity_flag` column in the dataset is an **unlabeled internal indicator**. The system does not know if it means a promotion, a specific campaign, or an organic merchandising event. The schema enforces this caveat: `"activity_flag is unlabeled and should be treated as an unknown internal activity indicator."`

**Key finding:** 40% of sales came from products under this unconfirmed flag. This is large enough to matter, but the agent correctly refused to call it a "promotion" — it labelled it as a potential confound requiring investigation.

---

#### `calendar_weather_agent` — Calendar and weather context

**Focus:** Assess calendar, inferred holiday, and weather context.

**Tools called:**
1. `get_calendar_weather_context` → `holiday_flag: true`; `holiday_name_inferred: labor_day_period`; temp: 19.98°C; humidity: 74%; precipitation: 2.35mm; wind: 1.29 level (calm)
2. `get_signal_evidence` → signal context

**Key finding:** Weather was **mild and favourable** for shopping — low precipitation, comfortable temperature. The `holiday_flag` was set, and `labor_day_period` was inferred from the date (May 1 = International Labour Day, a national holiday in China). The agent flagged the critical caveat: the holiday name is **inferred, not confirmed** from an official calendar.

---

### 3.4 Node: Critic

**What the critic does:** Reads all six agent memos plus the evidence ledger. Returns a structured JSON verdict: should the loop continue? What gaps remain?

**Critic system prompt:**

```
You are the critic for a retail RCA investigation loop. Return valid JSON only.
Schema: {"continue_investigation":<bool>,"confidence_ceiling":"low|medium|high",
"gaps":[{"id":"gap_001","description":"...","severity":"low|medium|high",
"gap_type":"missing_internal_evidence|missing_external_context|weak_causal_link|
baseline_conflict|scope_violation|format_violation|insufficient_business_action|unavailable_data",
"suggested_agents":[...],"suggested_tools":[...]}],
"recommended_agents":[...],"recommended_tools":[...],"stop_reason":"..."}
Set continue_investigation=false when: confidence_ceiling is high and gaps are minor,
all remaining gaps are unavailable_data, or sufficient evidence exists.
Do not identify product or store as root causes.
Do not use dollar signs, revenue, profit, or margin.
[+ critic.md skill file]
```

**User message sent to critic:** The city/date, round index, evidence count, last 5 evidence items, and the full text of all 6 agent memos concatenated.

**Critic verdict for May 1:**

```json
{
  "continue_investigation": false,
  "confidence_ceiling": "high",
  "stop_reason": "Confidence ceiling is high: the lift is consistently observed across multiple 
    baselines (+14% to +26%), supported by a plausible holiday context (inferred Labor Day period), 
    broad but shallow discounting, and a morning-heavy intraday shape consistent with a demand event. 
    Remaining gaps (unlabeled activity, inferred holiday, unweighted stockouts) are minor or 
    unavailable_data, and further investigation is unlikely to change the core narrative.",
  "gaps": [
    {
      "id": "gap_001",
      "gap_type": "missing_internal_evidence",
      "severity": "medium",
      "description": "The 'activity_flag' is unlabeled and cannot be definitively mapped to a 
        promotion, campaign, or other specific business action."
    },
    {
      "id": "gap_002",
      "gap_type": "missing_external_context",
      "severity": "medium",
      "description": "The holiday name 'labor_day_period' is inferred from date context, not from 
        a confirmed source."
    },
    {
      "id": "gap_003",
      "gap_type": "unavailable_data",
      "severity": "low",
      "description": "Stockout rates are not velocity-weighted; impact on top-selling SKUs may 
        be understated."
    }
  ]
}
```

**`continue_investigation: false`** — the loop stops after round 1.

> **Why stop here?** The critic's stop logic: `confidence_ceiling` is `"high"` AND the remaining gaps are either `missing_internal_evidence` (unlabeled flag — cannot be resolved with available tools) or `unavailable_data` (velocity-weighted stockouts — tool doesn't exist). Gap 002 is `missing_external_context` but its severity is only medium — the news agent would not materially change the conclusion. The critic correctly judges that running a second round would waste tokens without changing the answer.

> **Note on `gap_002`:** This gap suggests `news_agent` could help confirm the holiday. But the news agent gate requires the critic to flag `missing_external_context` **and** a second round to exist. Since `continue_investigation=false`, this gap never gets acted on. This is intentional — it's acknowledged as an open question in the caveats, not silently ignored.

---

### 3.5 Node: Decision Brief (Coordinator)

**What the coordinator does:** Takes the full investigation state and produces the final structured `DecisionBrief` JSON plus the human-readable markdown report. This is the most important LLM call and runs on the **deep model** (`deepseek-v4-pro`).

**Coordinator system prompt:**

```
You are the final synthesis coordinator for a retail RCA. Return valid JSON only.
sale_amount and hours_sale are normalized sales amounts from the source dataset.
Treat them as relative sales amounts for comparison, not currency and not literal units.
Schema: {"headline":"<one line>","confidence":"low|medium|high",
"situation":"<2-3 sentences>","business_impact":"<1-2 sentences>",
"most_likely_explanation":"<2-3 sentences>","evidence_summary":["<bullet>",...],
"recommended_action":"<1-2 sentences>","alternatives":["<alt>,..."],
"owner_function":"<function>","urgency":"low|medium|high","expected_benefit":"<1 sentence>",
"monitoring_plan":{"metrics_to_watch":[...],"review_horizon":"...","escalation_trigger":"..."},
"unknowns":["<unknown>",...],"caveats":["<caveat>,...]}
Rules:
- Do not mention product or store as root causes.
- Do not use dollar signs, revenue, profit, or margin without explicit data.
- Use 'insufficient evidence' when data is absent. Do not force a cause.
- External evidence is supportive only; internal facts are primary.
[+ coordinator.md skill file]
```

**User message:** Signal dict, investigation round count, evidence count, evidence summaries (last 10), last critic review, recent memory notes.

**Final `DecisionBrief` produced:**

```
headline:     "Strong sales lift on May 1 driven by broad holiday demand and shallow 
               discounting, with unlabeled activity as a likely contributor."
confidence:   high
urgency:      low
owner_function: Marketing
```

**Situation (2-3 sentences):**
> On Wednesday, May 1, 2024, city 0 recorded total sales of 27,610, a +26.2% increase over the same-weekday-4w baseline of 21,874. The lift is consistent across multiple baselines (+14% to +26%) and concentrated in morning hours, aligning with an inferred Labor Day period. No major internal disruptions were detected; inventory availability was adequate, and pricing pressure was broad but shallow.

**Most likely explanation:**
> The sales lift is primarily attributable to elevated consumer demand during the inferred Labor Day period, amplified by broad, shallow discounting and a high rate of unlabeled promotional activity. The morning-heavy intraday pattern is consistent with a holiday-driven shopping surge. Internal factors (adequate inventory, no major pricing anomalies) did not constrain the lift, but the unlabeled activity flag suggests an unconfirmed campaign or organic merchandising push contributed.

**Evidence summary bullets:**
- Sales of 27,610 exceeded the same-weekday-4w baseline by +26.2%, with consistent lifts across multiple baselines (+14% to +26%).
- Intraday sales were morning-heavy, consistent with a holiday demand pattern.
- Discount depth was shallow and coverage broad, indicating promotional support without deep margin pressure.
- Unlabeled activity accounted for 40.1% of products and 39.5% of sales, suggesting an unconfirmed internal campaign or merchandising action.
- Inventory availability was adequate; stockout rates were not velocity-weighted, but no critical shortages were flagged.
- The date is inferred as a Labor Day period, though local holiday observance is unverified.

**Recommended action:**
> Review and label the unlabeled activity to confirm whether it was a planned campaign or organic merchandising. If planned, codify the playbook for future holiday periods; if organic, investigate the specific SKUs and categories that drove the lift to replicate the effect.

**Unknowns acknowledged:**
- Exact nature and cause of the unlabeled activity
- Whether the inferred Labor Day period is actually observed in this city
- Velocity-weighted stockout impact on top-selling SKUs

**Caveats acknowledged:**
- Sales amounts are normalized and relative; not currency
- Holiday name is inferred from date context, not confirmed
- Stockout analysis is not velocity-weighted

The coordinator then calls `_brief_to_markdown()` which assembles the brief fields into the formatted `final_report` markdown stored in `outcomes.report_markdown`.

---

### 3.6 Node: Evaluation

**What evaluation does:** Runs 8 deterministic rule-based checks on the final decision brief. No LLM is called for these checks — they are pure Python regex/logic.

**The 8 deterministic checks and their results for May 1:**

| Check name | Severity | Passed? | What it tests |
|---|---|---|---|
| `no_currency_terms` | high | ✅ | No dollar signs, USD, CNY, or computed revenue figures |
| `no_product_store_root_cause` | high | ✅ | Root cause does not mention products or stores by ID |
| `evidence_non_empty` | medium | ✅ | Evidence ledger has at least one item |
| `headline_non_empty` | medium | ✅ | A headline was produced |
| `confidence_calibration` | medium | ✅ | Confidence level is within expected range given round count |
| `unknowns_when_thin_evidence` | low | ✅ | When evidence is thin, unknowns section is populated |
| `external_not_sole_source` | medium | ✅ | External/news evidence was not the only evidence cited |
| `monitoring_plan_populated` | low | ✅ | Monitoring plan has at least one metric to watch |

**Score: 1.0 (8/8 passed)** — a perfect deterministic score.

> **Note on the LLM judge in `evaluation_json`:** The `llm_judge` sub-object shows `"enabled": false` in the stored record. This is because `RCA_LLM_JUDGE_ENABLED` routes through `evaluation_node` but the alignment judge was also called separately via `review_outcome()` (see section 3.7). The flags in the stored JSON reflect that the in-node LLM call was bypassed — the full alignment judge output is stored in `alignment_*` fields alongside the deterministic checks.

---

### 3.7 Node: Alignment Reviewer (LLM Judge)

**What the reviewer does:** After the deterministic checks, the `evaluation_node` calls `review_outcome()` when `RCA_LLM_JUDGE_ENABLED=true`. This sends the full `DecisionBrief` JSON + the evidence ledger to the **deep model** (`deepseek-v4-pro`) with a structured rubric prompt. The reviewer grades the output against the project's core guardrails.

**Reviewer system prompt (`REVIEWER_ALIGNMENT_PROMPT`):**

```
You are a quality reviewer for retail RCA (root cause analysis) outputs.
Your job is to assess how well an RCA decision brief aligns with the project's 
core guardrails and usefulness criteria.

## Core guardrails (hard rules)
1. Output must stay at city/date grain. No product identifiers, SKU numbers, or store 
   numbers in root cause claims.
2. sale_amount and hours_sale are normalized amounts, not currency. No dollar signs, 
   USD, CNY, or computed revenue/profit/margin figures.
3. Internal Supabase facts are the primary evidence source. External/news evidence 
   is supportive only.
4. Confidence must be calibrated to evidence volume. High confidence requires 
   substantial internal evidence.
5. "Insufficient evidence" and "unknown" are valid, encouraged outcomes. Do not force 
   a root cause.

## Usefulness criteria (soft rules)
6. The recommended action must be specific and actionable for the named owner function.
7. The monitoring plan must specify concrete metrics to watch, not vague outcomes.
8. Evidence claims must be traceable — not fabricated from the signal alone.
9. Caveats must acknowledge data limitations honestly (unlabeled activity_flag, 
   inferred holiday names, synthetic goals).

## Output format
Return ONLY valid JSON — no prose, no markdown, no explanation before or after.
{
  "alignment_score": <float 0.0–1.0>,
  "alignment_label": <"aligned" | "partial" | "misaligned">,
  "pros": [<2–4 specific strengths>],
  "cons": [<2–4 specific violations or weaknesses>],
  "improvements": [<2–4 concrete suggestions>],
  "comment": <one-sentence overall verdict>
}
Scoring: aligned 0.75–1.00 | partial 0.40–0.74 | misaligned 0.00–0.39
```

**User message sent to reviewer:** The full `DecisionBrief` JSON, the Decision Card markdown, evidence count/type summary, and the deterministic check results.

**Reviewer verdict for May 1:**

```
alignment_score: 0.82
alignment_label: aligned
comment: "A well-structured RCA with strong internal evidence and honest caveats, 
          but confidence should be tempered given the large unknown share and 
          unconfirmed holiday."
```

**Pros identified:**
- Clear attribution of the lift to a holiday period, supported by consistent intraday patterns and multiple baseline comparisons.
- Actionable recommendation for Marketing to label unconfirmed activity and codify future playbooks.
- Honest acknowledgment of unknowns including the nature of unlabeled activity, holiday confirmation, and velocity-weighted stockouts.
- Caveats explicitly address data normalization, inferred holiday, and analytical limitations.

**Cons identified:**
- Confidence rated 'high' despite unlabeled activity accounting for 40.1% of products and 39.5% of sales, with the exact nature unknown and possibly a data artifact.
- The most likely explanation treats the inferred Labor Day period as the primary driver, but the brief acknowledges the holiday observance is unverified.

**Improvements suggested:**
- Reduce confidence to 'medium' to reflect the uncertainty from high unlabeled share and unconfirmed holiday.
- Include a direct validation step with a confirmed local holiday calendar to strengthen the external demand claim.
- Add velocity-weighted stockout analysis in the monitoring plan to better assess inventory impact on top items.
- Flag the unlabeled activity as a potential data quality issue that may require infrastructure investigation, not just marketing review.

> **Analyst note:** The reviewer disagreed with the coordinator on confidence level. The coordinator rated it `"high"` (because the signal is robust across multiple baselines); the reviewer argued for `"medium"` (because 40% of the lift is from an unconfirmed source). This tension is real and reflects a genuine calibration debate — the score of 0.82 says the output is solid but not perfect.

---

### 3.8 Node: Memory Distiller

**What memory distiller does:** Receives the `final_report` markdown and extracts 3–5 reusable lessons that a future investigation of city 0 should remember.

**System prompt:**

```
Write short reusable city lessons from one RCA run.
Return markdown with section ## Lessons and 3-5 bullets.
Only extract lessons that are directly supported by evidence in the final report 
— do not generalize beyond what was observed in this specific run.
[+ memory_distiller.md skill file]
```

**User message:** The full `final_report` markdown text.

**Lessons produced and written to `rca.memory`:**

```markdown
## Lessons

- **Broad holiday demand can mask the impact of specific campaigns.** The May 1 lift 
  was attributed to general holiday shopping, but unlabeled activity was a likely 
  contributor — always isolate unlabeled traffic early to avoid misattributing lift 
  to baseline demand.

- **Shallow discounting does not rule out strong sales lifts.** Even with modest 
  promotions, holiday-driven demand can produce significant uplifts; do not assume 
  deep discounts are necessary for a spike.

- **Cross-reference unlabeled activity with holiday calendars.** When a lift coincides 
  with a known holiday, check whether unlabeled traffic patterns align with the holiday 
  surge to avoid overlooking hidden drivers.

- **High confidence in a cause does not eliminate the need to verify unlabeled sources.** 
  Even with a clear headline, always audit unlabeled activity as a potential confound 
  before finalizing conclusions.
```

These lessons are stored with `influence_score: 0.5`. On the next run for city 0 (the June 9 drop), the planner will receive these lessons as prior context.

---

### 3.9 Final Output Written to Database

After memory distillation, the `record` node persists everything to Supabase in a single flush. Summary of what was written:

| Table | Rows written | Contents |
|---|---|---|
| `rca.outcomes` | 1 | Full run result with all JSON blobs |
| `rca.events` | ~30 | One started/completed event per node and tool |
| `rca.completions` | ~15 | One row per LLM API call (planner × 1, each agent × ~2 calls, coordinator × 1, reviewer × 1, memory distiller × 1) |
| `rca.memory` | 1 | Lessons from this run |
| `rca.evidence_cache` | ~10 | Cached Supabase query results |

**Total LLM calls:** ~15 (planner: 1; 6 specialists × ~2 each: 12; critic: 1; coordinator: 1; reviewer: 1; memory distiller: 1)

---

## 4. Case Study 2 — June 9, 2024: Dragon Boat Festival Drop

**Run ID:** `city_0_2024-06-09_20260621T172532_SGT`  
**Signal:** `drop` · **Deviation:** `-18.6%` · **Confidence:** `medium`

### 4.1 Signal Context

**Signal row for city 0 on 2024-06-09:**

```
signal_label:          drop
goal_method:           same_weekday_4w      ← 4-week Sunday average
current_sales:         28,147
expected_sales:        34,574               ← prior 4 Sundays average (holiday-inflated)
deviation_pct:         -18.6%               ← below drop threshold of -10%
holiday_name_inferred: dragon_boat_period   ← June 10, 2024 = Dragon Boat Festival
weekday:               sunday
signal_strength:       moderate
priority_score:        23.59
```

**Critical context not in the signal row:** The prior 4 Sundays (May 12, 19, 26, Jun 2) included pre-festival shopping days with elevated demand. This inflated the 4-week Sunday average to 34,574 — making the festival Sunday itself look like a drop even though absolute sales were strong at 28,147.

---

### 4.2 Node: Planner

**New element vs Run 1:** The planner now receives the memory from Run 1 (the May 1 Labour Day lessons).

**Memory notes passed to planner:**
```
- Broad holiday demand can mask the impact of specific campaigns.
- Shallow discounting does not rule out strong sales lifts.
- Cross-reference unlabeled activity with holiday calendars.
- High confidence in a cause does not eliminate the need to verify unlabeled sources.
```

**Effect of memory:** The planner's `memory_context_json` records `"used": true`, `"effect": "Memory notes provided to planner."` The planner was told about the unlabeled activity confound from the prior run before selecting agents. This is the **learning mechanism** — without memory, the planner would start fresh each time.

**Planner decision:** Same six internal agents selected (statistician, sales_agent, inventory_agent, pricing_agent, promotions_agent, calendar_weather_agent). No `news_agent` in round 1.

---

### 4.3 Node: Specialist Agents (Parallel)

#### `statistician` — The key statistical tension

The statistician immediately detected a **baseline conflict** — the two baseline methods gave opposite signals:

| Baseline | Value | Delta |
|---|---|---|
| Same-weekday-4w | 34,574 | **-18.6%** (drop signal) |
| Recent 7-day rolling | 26,406 | **+6.6%** (above trend) |

This is the most interesting finding in the entire run. The same sales figure (28,147) looks like a drop vs 4-week Sunday history but a lift vs recent daily trend. The statistician correctly identified this as the core analytical problem.

**Tools called:**
1. `get_signal_evidence` → `-18.6%`, holiday: `dragon_boat_period`
2. `get_sales_context` → 14-day history: prior Sundays (Jun 2: 32,651; May 26: 34,200) were very high
3. `compare_recent_baseline` → **+6.6%** vs 7-day average (contradicts the signal!)
4. `compare_same_weekday_baseline` → **-18.6%** vs 4-week Sunday average (matches the signal)
5. `get_intraday_profile` → morning peak again at 09:00 (13.14% share), similar to May 1
6. `detect_intraday_shift` → hours 8/9/10 elevated vs baseline; hour 16 reduced
7. `run_stat_analysis` × 3:
   - `simple_expected_sales_sanity_check`: -18.6% is material
   - `robust_baseline_check`: confirmed the 4-week baseline shows -18.6%
   - `driver_shift_scan`: intraday shift is similar in shape to May 1 (morning-heavy)

**Statistician inference (excerpt):**
> "City 0 on 2024-06-09 triggered a **'drop' signal** at -18.6% below expected sales. Validating this signal is critical because: a false positive could trigger unnecessary investigation or inventory actions. The Dragon Boat Festival period (inferred holiday) may naturally shift sales patterns, making baseline comparisons unreliable."

---

#### `sales_agent`

Noted that while the signal is a "drop", the actual sales of 28,147 are higher than many recent weekdays. The agent flagged the baseline mismatch: "Sales on 2024-06-09 came in at **28,147**, which is **18.6% below what was expected**... While not a catastrophic collapse, this is a meaningful shortfall that warrants attention, especially given the timing during the **Dragon Boat Festival period** — a holiday window that typically lifts sales."

---

#### `inventory_agent`

**Notable difference vs May 1:** Stockout product rate jumped to **39.6%** (up from 31.1% on May 1). Severe stockout rate: **16.3%** (up from 13.6%). Average stockout hours: 2.80 (up from 2.28).

The inventory agent correctly observed: "Sales on 2024-06-09 were +6.6% above the 7-day baseline... Understanding whether availability pressure constrained or shaped this outcome is critical: if stockouts were high, the true demand may have been even stronger (lost sales)."

Higher stockouts on this day vs May 1 suggest the drop might have been partially demand constrained — but the agent acknowledged this is speculative without velocity-weighted data.

---

#### `pricing_agent`

**Pricing on June 9 vs May 1:**

| Metric | May 1 (lift) | Jun 9 (drop) |
|---|---|---|
| Avg discount | 0.921 (7.9% off) | 0.890 (11.0% off) |
| Discounted product rate | 50.7% | 61.7% |
| Deep discounted rate | 0% | 1.44% |

On the "drop" day, the store actually applied **more aggressive discounting** — deeper discounts, wider coverage, and some deep discounts appeared. Yet sales still fell against the 4-week baseline. The pricing agent noted this as a diagnostic signal: discounting increased but didn't compensate, suggesting the drop was not primarily pricing-related and may be a genuine demand shift (or baseline inflation effect).

---

#### `promotions_agent`

`activity_flag` rate: **46.5% of products, 44.5% of sales** — even higher than May 1. Yet sales dropped. The promotions agent's memo: "This date falls within the **Dragon Boat Festival period** (a holiday window), and the signal is classified as a **'drop'** — meaning sales fell significantly below what would normally be expected. Understanding whether an internal activity or promotion was running (or not) helps explain whether this drop occurred *despite* promotional efforts, or *because* no effective promotion was in place."

The agent concluded: the high activity flag rate suggests the store was running activity, but its effectiveness is unclear given the drop signal.

---

#### `calendar_weather_agent`

**Weather on June 9:**
```
temperature:  26.3°C (warm summer day)
humidity:     77.3%
precipitation: 5.18mm (light rain)
wind_level:   1.41 (light breeze)
holiday_flag: true
holiday_name_inferred: dragon_boat_period
weekday:      sunday (is_weekend: true)
```

Light rain on a Sunday holiday. The agent noted: "Moderate weather may have shifted shopping patterns" but was appropriately cautious — 5mm of precipitation is light and unlikely to be the primary driver.

---

### 4.4 Node: Critic

**Critic verdict for June 9:**

```json
{
  "continue_investigation": false,
  "confidence_ceiling": "medium",
  "stop_reason": "The -18.6% drop is plausibly explained by the Dragon Boat Festival 
    holiday period (inferred) combined with moderate weather dampening. The baseline 
    conflict and unlabeled activity flag introduce uncertainty, but the holiday context 
    provides a sufficient explanation for the drop. Remaining gaps (product/store 
    breakdown, competitor data) are unlikely to change the primary narrative. 
    Confidence ceiling is medium due to unresolved baseline conflict and inferred 
    holiday naming.",
  "gaps": [
    {
      "id": "gap_001",
      "gap_type": "missing_external_context",
      "severity": "medium",
      "description": "The holiday name 'dragon_boat_period' is inferred from date context, 
        not source-labeled."
    },
    {
      "id": "gap_002",
      "gap_type": "missing_internal_evidence",
      "severity": "medium",
      "description": "The 'activity_flag' is unlabeled; it is not confirmed to be a 
        promotion, discount, or marketing campaign."
    },
    {
      "id": "gap_003",
      "gap_type": "baseline_conflict",
      "severity": "medium",
      "description": "The same-weekday-4w and 7-day-rolling baselines disagree. Without 
        knowing which prior Sundays fell inside vs outside the Dragon Boat Festival 
        period, it is unclear which baseline is more appropriate."
    },
    {
      "id": "gap_004",
      "gap_type": "missing_internal_evidence",
      "severity": "medium",
      "description": "No product-level or store-level breakdown available."
    },
    {
      "id": "gap_005",
      "gap_type": "missing_external_context",
      "severity": "low",
      "description": "No data on competitor pricing or category mix."
    }
  ]
}
```

**5 gaps identified vs 3 in May 1** — the drop case was genuinely more uncertain. The `baseline_conflict` gap (`gap_003`) is a new gap type that didn't appear in the lift case. The critic correctly capped confidence at `"medium"` rather than `"high"`.

---

### 4.5 Node: Decision Brief (Coordinator)

The coordinator (deep model) synthesised the baseline conflict as the central insight. Instead of treating the drop as a real demand problem, it identified the **methodological issue** with the baseline:

**Situation:**
> On Sunday, 2024-06-09, total sales reached 28,147, which is 18.6% below the expected 34,574 based on the same-weekday average over the prior four weeks. This date falls within the inferred Dragon Boat Festival period. A conflicting 7-day rolling baseline shows sales were actually 6.6% above the recent trend, suggesting the drop is relative to a high baseline rather than a sudden collapse.

**Most likely explanation:**
> The drop is most likely a **baseline effect**. The same-weekday-4w baseline includes pre-festival Sundays with peak holiday shopping, inflating the expected value. The actual sales on the festival Sunday itself were still strong compared to the recent 7-day trend. Moderate weather may have further shifted shopping patterns, but the core issue is a mismatch between the comparison period and the holiday demand curve.

**Recommended action:**
> Recalibrate the baseline for holiday periods to use a pre-festival comparison window that avoids peak demand days. Investigate the unlabeled activity flag to determine if it represents a pull-forward mechanism.

**Owner function:** Planning & Analytics (not Marketing as in Run 1 — the issue here is measurement methodology, not campaign execution)

**Caveats:**
- The holiday name 'dragon_boat_period' is inferred from the date, not a confirmed source label.
- The baseline conflict is unresolved; the 4-week baseline may be fundamentally inappropriate for this holiday Sunday.
- All sales figures are normalized and should be treated as relative comparisons, not absolute currency.

> **This is the coordinator at its best:** It didn't just accept the signal at face value. It used the conflicting baselines (a quantitative contradiction in the data) to challenge the premise of the signal itself. The recommended action is methodological (fix the baseline) rather than operational (do something about the sales). This is a qualitatively more sophisticated RCA than the lift case.

---

### 4.6 Node: Evaluation

**The 8 deterministic checks — all passed again (score: 1.0):**

| Check | Passed? |
|---|---|
| `no_currency_terms` | ✅ |
| `no_product_store_root_cause` | ✅ |
| `evidence_non_empty` | ✅ |
| `headline_non_empty` | ✅ |
| `confidence_calibration` | ✅ |
| `unknowns_when_thin_evidence` | ✅ |
| `external_not_sole_source` | ✅ |
| `monitoring_plan_populated` | ✅ |

> **Interesting point:** The headline mentions "Dragon Boat Festival Sunday" without hedging the inferred name. The calendar_weather_agent flagged it as inferred — and the caveats section in the brief correctly carries the caveat. But the headline itself dropped the qualifier. The alignment reviewer called this out (see below).

---

### 4.7 Node: Alignment Reviewer (LLM Judge)

**Reviewer verdict for June 9:**

```
alignment_score: 0.90
alignment_label: aligned
comment: "The brief is well-aligned with guardrails, offering a thoughtful baseline-relative 
          explanation despite a minor headline inconsistency and an unqualified inferred 
          holiday name."
```

**Pros identified:**
- Clearly distinguishes between a baseline conflict and a real demand drop, avoiding false alarm.
- Honestly acknowledges unknown activity flag and inferred holiday, preserving intellectual honesty.
- Recommends a specific, actionable baseline recalibration directly within the Planning & Analytics remit.
- Monitoring plan lists concrete, trackable metrics and a clear escalation trigger.

**Cons identified:**
- Headline frames moderate weather as equally likely cause alongside pull-forward, but main explanation treats it as a minor factor only. (Inconsistency between headline and body.)
- Headline uses 'Dragon Boat Festival Sunday' without qualification, while caveats admit the holiday period is inferred from dates.
- Alternative 'moderate weather suppressed foot traffic' lacks direct evidence in the ledger and is not substantiated further.

**Improvements suggested:**
- Revise headline to emphasize baseline mismatch (e.g., "...driven by inflated same-weekday baseline from holiday pull-forward") and reduce weather's prominence.
- Prefix inferred holiday names with 'expected' or 'likely' in the headline and key statements.
- Suggest correlating the unlabeled activity flag with prior Sunday sales spikes to test the pull-forward hypothesis before acting.
- Add a note in monitoring to track weather data alongside sales during holidays to isolate its effect in future analyses.

> **The drop run scored higher (0.90) than the lift run (0.82).** Counterintuitive? The reason: the drop case's coordinator was more intellectually honest — it challenged the signal's premise, stayed appropriately at `"medium"` confidence, and produced a more methodologically sound recommendation. The reviewer rewarded restraint and honest uncertainty over confident but unverified attribution.

---

### 4.8 Node: Memory Distiller

**Lessons written to `rca.memory` for city 0, June 9:**

```markdown
## Lessons

- **Holiday demand pull-forward can mask true performance:** A single-day sales drop 
  may reflect pre-holiday buying rather than a structural decline. Always compare 
  multi-day windows (e.g., the full holiday weekend) before concluding a trend.

- **Weather moderation is a plausible confound:** When sales dip on a holiday, check 
  if mild weather reduced urgency for seasonal purchases. This can explain part of 
  the drop without implying a demand problem.

- **Confidence in a single-day signal is limited:** A medium-confidence conclusion 
  based on one day's data should trigger deeper investigation (e.g., same-store vs. 
  online splits, competitor activity) before acting on the signal.
```

Three lessons vs four in May 1 — the distiller correctly produced fewer, tighter lessons because the June 9 case was less conclusive.

---

### 4.9 Final Output Written to Database

| Table | Rows written | Contents |
|---|---|---|
| `rca.outcomes` | 1 | Full run result; `memory_context_json` shows `"used": true` |
| `rca.events` | ~30 | Execution trace |
| `rca.completions` | ~15 | All LLM API calls |
| `rca.memory` | 1 | Drop-day lessons |
| `rca.evidence_cache` | ~10 | Some cache hits (overlapping queries with May 1 run) |

---

## 5. Cross-Run Comparison

| Dimension | May 1 — Labour Day Lift | Jun 9 — Dragon Boat Drop |
|---|---|---|
| **Signal** | +26.2% lift | -18.6% drop |
| **Confidence** | high | medium |
| **Investigation rounds** | 1 | 1 |
| **Evidence items** | 26 (ev_001–ev_026) | 26 (ev_001–ev_026) |
| **Agents selected** | 6 internal | 6 internal |
| **News agent fired?** | No | No |
| **Critic gaps** | 3 | 5 |
| **Key insight** | Holiday + unlabeled activity drove the lift | **The signal itself may be a baseline artefact** |
| **Recommended owner** | Marketing | Planning & Analytics |
| **Urgency** | Low | Low |
| **Deterministic eval score** | 1.0 (8/8) | 1.0 (8/8) |
| **Alignment score** | 0.82 | **0.90** |
| **Alignment label** | aligned | aligned |
| **Memory used?** | No (first run) | Yes (May 1 lessons loaded) |
| **Memory lessons written** | 4 | 3 |

**The most interesting contrast:** The drop case is a better RCA than the lift case, even though the signal was harder to interpret. The coordinator challenged the measurement methodology rather than accepting the signal at face value. The lift case accepted the +26.2% as real (which it was) and attributed it to holiday demand — correct but simpler. The drop case required the model to reconcile two contradictory baselines and choose the more defensible interpretation.

**Baseline conflict** is a failure mode the system is explicitly designed to detect. The critic has a dedicated `"baseline_conflict"` gap type for exactly this scenario. The coordinator then acted on it in synthesis.

---

## 6. Architecture and Production Design Review

### What this system does well

**Structured multi-agent decomposition.** The investigation is split into specialist agents that each own a narrow domain. This prevents one LLM call from trying to simultaneously reason about statistics, inventory, pricing, and promotions — a common failure mode in single-prompt approaches. Each specialist has a focused tool set and a narrow mandate.

**Deterministic guardrails before LLM judgement.** The 8-check audit runs before any LLM quality scoring. Currency terms, product/store root causes, empty headlines — these are checked with regex and logic, not by asking the model if it violated them. The LLM reviewer then adds nuance on top. This layering (deterministic-first, LLM-second) is correct design: fast, cheap, reliable checks first, expensive judgement second.

**Evidence ledger as a first-class artifact.** Every observation (tool call result) and inference (agent memo) is typed, ID'd, and persisted. This makes the reasoning traceable — you can reconstruct exactly which data each inference was drawn from. The reviewer prompt explicitly instructs: "cons must quote or paraphrase a specific claim from the supplied brief or evidence — not a general quality concern." This grounds the LLM review in the actual run, not vague impressions.

**Bounded investigation loop.** The critic's stop conditions are explicit: stop if `confidence_ceiling` is high and gaps are minor; stop if all gaps are `unavailable_data`; stop at `RCA_MAX_INVESTIGATION_ROUNDS`. This prevents infinite loops and keeps cost predictable. In both these runs, one round was sufficient — the system correctly did not run a wasteful second round.

**Memory across runs.** Lessons from each run are stored and loaded for subsequent runs of the same city. In the June 9 run, the planner received four lessons from May 1 — the most directly relevant being "cross-reference unlabeled activity with holiday calendars." This is a lightweight but effective form of institutional memory at the agent level.

**Confidence calibration is enforced, not suggested.** The coordinator prompt says "High confidence requires substantial internal evidence." The critic enforces this by setting `confidence_ceiling` before synthesis. The reviewer grades calibration explicitly. Both layers together push back against overconfident outputs — the June 9 run is the proof: even with a clear narrative, the system settled on `"medium"`.

**Parallelism without shared state.** The six specialist agents run in a `ThreadPoolExecutor` and do not share a conversation history. This is intentional — it prevents agents from anchoring on each other's conclusions. The critic sees all memos and synthesises them after the fact.

---

### Where the design has gaps

**Single-day grain is a structural limitation.** Both runs investigated one calendar day in isolation. The June 9 case showed the risk clearly: a single-day signal triggered by a holiday baseline mismatch is almost meaningless without the multi-day window around it. The agent correctly identified this but could not resolve it — the data model doesn't provide adjacent-day context natively. The recommended action (recalibrate the baseline) requires work outside the agent.

**`activity_flag` opacity blocks a key dimension.** The unlabeled activity flag appeared in both runs as a major uncertainty. In May 1, 39.5% of sales came from flagged products — and the system could not determine if this was a planned campaign, organic activity, or a data quality artefact. In June 9, it was 44.5% of sales. This gap will recur in every RCA until the upstream data pipeline labels this column. An agent system cannot fix data governance issues — it can only flag them, which it did correctly.

**No velocity-weighted stockout analysis.** The stockout check (`get_inventory_context`) returns product counts and average hours. It does not weight by sales velocity, so a stockout on a high-velocity product (which could suppress thousands of units of sales) looks identical to a stockout on a slow-moving item. The critic flagged this in both runs as `"unavailable_data"` — meaning the gap is known but the tool doesn't exist yet. Building a velocity-weighted stockout tool would meaningfully improve RCA quality.

**News agent gating may be too conservative.** The news agent requires: (a) round 2 or later, (b) an internal evidence round already completed, (c) critic identified `missing_external_context`. In these runs, the critic correctly identified `missing_external_context` gaps (holiday confirmation), but since `continue_investigation=false`, the news agent never fired. A holiday lookup tool that runs deterministically — not through the agent loop — would be cheaper and more reliable than the web search approach.

**Memory influence score is static.** Every lesson is stored with `influence_score: 0.5` regardless of run quality. If a run produced a bad RCA (low alignment score), its lessons are stored with the same weight as a high-quality run. A feedback loop from alignment scores into memory influence weights would improve learning quality over time.

**Token cost scales with evidence size.** The coordinator receives evidence summaries (last 10 items) and the critic receives agent memos. As the number of investigation rounds grows, so does the context sent to both. In a 5-round run, the coordinator's context could be 2–3× larger than in a 1-round run. There is no compression or selective evidence retrieval — the raw summaries are passed verbatim.

**No human-in-the-loop checkpoint.** The system produces and persists a final decision brief without any human review gate. For a production system where recommendations could drive inventory or marketing decisions, there should be a review queue: the agent produces a draft, a human approves or rejects before it goes to the downstream owner. The current design assumes the recommendation is advisory and non-binding — appropriate for a sandbox, but not for production.

**The `same_weekday_4w` baseline is a known limitation for holiday periods.** The June 9 drop is a textbook example: the 4-week prior Sunday window included pre-festival shopping Sundays, inflating the baseline. This is a known, systematic error that will recur on any holiday Sunday in the dataset. The fix (holiday-aware baseline that excludes other holiday periods) needs to be implemented in `rca/database.py` in the signal materialization step — it cannot be patched by the agent at query time.

---

### Summary Assessment

The system is a well-designed prototype with a clear chain of responsibility: specialist → critic → coordinator → evaluator → reviewer → memory. The layering of deterministic checks before LLM judgement is sound engineering. The evidence ledger is the right abstraction for traceability.

The two runs demonstrate that the system handles a confident positive case (Labour Day lift) and a methodologically ambiguous negative case (Dragon Boat baseline conflict) with appropriate differentiation in confidence and in the type of recommendation produced. The alignment scores (0.82 and 0.90) are honest — neither run is perfect, and the reviewer correctly identified the remaining gaps.

The primary risks for production are: data governance (the `activity_flag` opacity), baseline methodology (holiday-aware signals), and the absence of a human review gate before recommendations reach operators. These are upstream data pipeline and process design issues, not agent architecture issues.
