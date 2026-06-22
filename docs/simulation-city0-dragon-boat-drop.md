# RCA Flow Simulation — City 0, Jun 9 2024 (Dragon Boat Festival Drop)

**Signal:** `drop` · **Deviation:** `-18.6%` · **Confidence:** `medium`  
**Purpose:** Step-by-step trace showing every stage prompt and response with real data.

---

## Stage 0 — Signal Trigger (no LLM)

`rca signal` runs a deterministic SQL/pandas pipeline. No LLM involved.

```
signal_label:     drop
current_sales:    28,147
expected_sales:   34,574      ← 4-week Sunday average (May 12, 19, 26, Jun 2)
deviation_pct:    -18.6%      ← below the -10% drop threshold
holiday_inferred: dragon_boat_period
weekday:          sunday
signal_strength:  moderate
```

`-18.6% < -10%` → signal fires. The prior four Sundays included pre-festival elevated days, inflating the expected value to 34,574 — this becomes the core analytical tension the agents must resolve.

---

## Stage 1 — Planner

**What it does:** Reads signal + sales history + calendar + prior memory. Returns which agents to dispatch and why.

**System prompt:**
```
You are planning a city/date retail RCA investigation round. Return valid JSON only.
Allowed agents: statistician, sales_agent, inventory_agent, pricing_agent,
promotions_agent, calendar_weather_agent, news_agent.
Round 1: always include statistician and sales_agent.
External web research is enabled.
Return JSON: {selected_agents, rationale, news_query, objective,
target_gaps, expected_evidence}
```

**User message (real data):**
```json
{
  "city_id": 0,
  "dt": "2024-06-09",
  "round_index": 1,
  "signal": {
    "signal_label": "drop",
    "deviation_pct": -18.6,
    "holiday_name_inferred": "dragon_boat_period",
    "current_sales": 28147,
    "expected_sales": 34574
  },
  "sales": {
    "current_total_sales": 28147,
    "history": [
      { "dt": "2024-06-02", "sale_amount": 32651 },
      { "dt": "2024-05-26", "sale_amount": 34200 },
      { "dt": "2024-05-19", "sale_amount": 33891 }
    ]
  },
  "calendar_weather": {
    "holiday_flag": true,
    "holiday_name_inferred": "dragon_boat_period",
    "avg_temperature": 26.3,
    "precipitation": 5.18
  },
  "memory": [
    "Broad holiday demand can mask the impact of specific campaigns.",
    "Cross-reference unlabeled activity with holiday calendars.",
    "High confidence does not eliminate the need to verify unlabeled sources."
  ]
}
```

**Planner output:**
```json
{
  "selected_agents": [
    "statistician", "sales_agent", "inventory_agent",
    "pricing_agent", "promotions_agent", "calendar_weather_agent"
  ],
  "rationale": "Signal is a holiday-period drop. All six internal agents needed: statistician to validate baselines, inventory to check stockout pressure, pricing to check if discounting was aggressive enough, promotions and calendar for holiday context. Prior memory flags unlabeled activity as a confound — promotions agent must check this.",
  "news_query": "Dragon Boat Festival 2024 Hong Kong Macau retail shopping",
  "objective": "Determine whether the -18.6% drop is real demand loss, a baseline artefact from elevated prior Sundays, or constrained supply."
}
```

> `news_agent` was not selected. Even if selected, a code gate in `run_investigation_loop` blocks it in round 1 — agents must gather internal evidence before going to web search.

---

## Stage 2 — Six Agents Run in Parallel

All six run simultaneously via `ThreadPoolExecutor`. Each gets its own independent LLM conversation.

**Shared system prompt template:**
```
You are a retail RCA agent focused on {focus}.
sale_amount and hours_sale are normalized sales amounts — treat as relative
comparison, not currency.
Use plain ASCII markdown. Distinguish observation from inference.
Return sections: ## Why It Matters  ## Evidence  ## Interpretation  ## Caveats
```

**User message:** `"Analyze city 0 on 2024-06-09. Focus: {focus}."`

Each agent then calls tools in a loop (up to 6 rounds) until it returns a memo with no tool call.

---

### Agent A — `statistician`

**Focus:** Validate the signal with runtime baselines, intraday shape, and descriptive statistics.

**Tools called:**

| # | Tool | Key result |
|---|---|---|
| 1 | `get_signal_evidence` | drop -18.6%, holiday dragon_boat_period |
| 2 | `get_sales_context` | prior Sundays: Jun 2 = 32,651; May 26 = 34,200 |
| 3 | `compare_recent_baseline` | **+6.6% vs 7-day rolling** ← contradicts signal |
| 4 | `compare_same_weekday_baseline` | **-18.6% vs 4-week Sunday** ← matches signal |
| 5 | `get_intraday_profile` | 09:00 peak = 13.14% of daily sales |
| 6 | `run_stat_analysis` ×3 | -18.6% is material; baseline conflict confirmed |

**Inference memo (stored as `ev_010`):**
> "The same sales figure of 28,147 looks like a -18.6% drop versus the 4-week Sunday average, but a +6.6% lift versus the 7-day rolling baseline. This is the core analytical problem. The prior four Sundays (May 12–Jun 2) included pre-festival elevated shopping days, inflating the expected value to 34,574. The festival Sunday itself may not be a real demand collapse — the baseline may be the problem."

---

### Agent B — `inventory_agent`

**Focus:** Assess whether stockout or availability pressure likely contributed to the move.

**Tools called:**

| # | Tool | Key result |
|---|---|---|
| 1 | `get_inventory_context` | stockout rate: **39.6%** of products (up from 31.1% on May 1); avg stockout hours: 2.80 |
| 2 | `get_intraday_profile` | stockouts low in morning peak, rise through afternoon |
| 3 | `compare_recent_baseline` | sales still +6.6% above recent trend |

**Inference:** "Higher stockouts vs the May 1 lift suggest the drop may be partially supply-constrained — actual demand could have been stronger. Speculative without velocity-weighted data."

---

### Agent C — `pricing_agent`

**Focus:** Assess discount depth and pricing pressure.

| Metric | May 1 (lift) | Jun 9 (drop) |
|---|---|---|
| Avg discount | 0.921 (7.9% off) | **0.890 (11.0% off)** |
| Discounted product rate | 50.7% | **61.7%** |
| Deep discounted rate | 0% | **1.44%** |

**Inference:** "Store applied more aggressive discounting on the drop day than the lift day — yet sales still fell against the 4-week baseline. If discounting increased but didn't compensate, the drop is not pricing-related. More consistent with a demand shift or baseline inflation effect."

---

### Agent D — `promotions_agent`

**Focus:** Assess the unlabeled activity indicator and possible promotion contribution.

`activity_flag` rate: **46.5% of products, 44.5% of sales** (higher than May 1's 40%). Yet sales dropped.

**Inference:** "High activity flag rate suggests the store was running something, but its effectiveness is unclear given the drop signal. Prior memory notes flagging unlabeled activity as a confound — treating this as the primary unknown."

---

### Agent E — `calendar_weather_agent`

**Focus:** Assess calendar, inferred holiday, and weather context.

```
temperature:    26.3°C
precipitation:  5.18mm (light rain)
wind:           1.41 (light breeze)
holiday_flag:   true
holiday_inferred: dragon_boat_period
weekday:        sunday
```

**Inference:** "Light rain on a warm Sunday holiday. Precipitation is low and unlikely to be the primary driver. Holiday context is plausible for a demand shift but the name is inferred from the date — not confirmed from an official calendar source."

---

### Agent F — `sales_agent`

**Focus:** Explain sales movement versus expected sales and recent history.

**Inference:** "Sales of 28,147 are 18.6% below what was expected. While not a catastrophic collapse, this is a meaningful shortfall. Notably, the actual figure is higher than many recent weekdays — the drop is relative, not absolute."

---

## Stage 3 — Critic

**What it does:** Reads all agent memos + evidence ledger. Decides whether to run another round, and what gaps remain.

**System prompt:**
```
You are the critic for a retail RCA investigation loop. Return valid JSON only.
Schema: {
  "continue_investigation": <bool>,
  "confidence_ceiling": "low|medium|high",
  "gaps": [{"id":"...","description":"...","severity":"low|medium|high",
            "gap_type":"missing_internal_evidence|missing_external_context|
                        baseline_conflict|unavailable_data|...",
            "suggested_agents":[...]}],
  "stop_reason": "..."
}
Set continue_investigation=false when: confidence_ceiling is high and gaps are minor,
all remaining gaps are unavailable_data, or sufficient evidence exists.
Do not identify product or store as root causes.
Do not use dollar signs, revenue, profit, or margin.
```

**User message:** city 0, Jun 9, round 1, evidence count = 14, last 5 evidence items, all agent memos concatenated.

**Critic output:**
```json
{
  "continue_investigation": false,
  "confidence_ceiling": "medium",
  "stop_reason": "The -18.6% drop is plausibly explained by a baseline effect — the 4-week Sunday average includes inflated pre-festival days. Sales vs the 7-day trend are actually positive (+6.6%). Remaining gaps are inferred holiday naming, unlabeled activity, and the baseline conflict — all unavailable_data or requiring external confirmation unlikely to change the core narrative.",
  "gaps": [
    {
      "id": "gap_001",
      "gap_type": "missing_external_context",
      "severity": "medium",
      "description": "Holiday 'dragon_boat_period' is inferred from date, not source-labeled."
    },
    {
      "id": "gap_002",
      "gap_type": "missing_internal_evidence",
      "severity": "medium",
      "description": "activity_flag is unlabeled — not confirmed to be a promotion or campaign."
    },
    {
      "id": "gap_003",
      "gap_type": "baseline_conflict",
      "severity": "medium",
      "description": "Same-weekday-4w and 7-day-rolling baselines disagree. Which prior Sundays fell inside the festival window is unknown."
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
      "description": "No competitor pricing or category mix data."
    }
  ]
}
```

`continue_investigation: false` → loop exits after **1 round**. 5 gaps identified (vs 3 on the May 1 lift — this case is genuinely more uncertain).

---

## Stage 4 — Coordinator (deep model)

**What it does:** Synthesises all evidence into a structured `DecisionBrief`. Runs on the deep model because nuance matters here.

**System prompt:**
```
You are the final synthesis coordinator for a retail RCA. Return valid JSON only.
sale_amount and hours_sale are normalized amounts, not currency.
Rules:
- Do not mention product or store as root causes.
- Do not use dollar signs, revenue, profit, or margin without explicit data.
- Use 'insufficient evidence' when data is absent. Do not force a root cause.
- External evidence is supportive only; internal facts are primary.
Schema: {"headline","confidence","situation","business_impact",
         "most_likely_explanation","evidence_summary","recommended_action",
         "alternatives","owner_function","urgency","monitoring_plan",
         "unknowns","caveats"}
```

**User message:**
```json
{
  "city_id": 0,
  "dt": "2024-06-09",
  "signal": { "signal_label": "drop", "deviation_pct": -18.6, "current_sales": 28147, "expected_sales": 34574 },
  "investigation_rounds": 1,
  "evidence_count": 14,
  "evidence_summaries": [
    "statistician: baseline conflict — +6.6% vs 7-day, -18.6% vs 4-week Sunday",
    "inventory_agent: stockout rate 39.6%, up from 31.1% on prior lift day",
    "pricing_agent: deeper discounting on drop day vs lift day — not compensating",
    "promotions_agent: activity flag 46.5% of products — purpose unlabeled",
    "calendar_weather_agent: light rain, warm, Dragon Boat period inferred"
  ],
  "last_critic_review": { "confidence_ceiling": "medium", "gaps": ["...5 gaps..."] },
  "recent_memory": [
    "Broad holiday demand can mask campaigns.",
    "Cross-reference unlabeled activity with holiday calendars."
  ]
}
```

**Coordinator output (the brief):**

**Headline:**
> Sales declined 18.6% against an inflated pre-festival Sunday baseline on Dragon Boat Festival Sunday, likely reflecting a baseline artefact rather than a real demand collapse.

**Most likely explanation:**
> The same-weekday-4w baseline includes pre-festival Sundays with peak holiday shopping, inflating the reference to 34,574. The festival Sunday itself (28,147) was actually +6.6% above the 7-day rolling trend. The apparent drop is most likely a measurement issue — the baseline period captured pull-forward demand, not a stable reference. Moderate weather may have further shifted shopping patterns, but the core issue is a mismatch between the comparison period and the holiday demand curve.

**Recommended action:**
> Recalibrate the baseline for holiday periods to exclude peak pre-festival shopping days. Investigate the unlabeled activity flag to determine if it represents a pull-forward mechanism.

**Owner function:** Planning & Analytics *(not Marketing — the issue is measurement methodology, not campaign execution)*

**Confidence:** medium

---

## Stage 5 — Evaluation (8 deterministic checks)

Python checks run against the `DecisionBrief` object. No LLM.

| Check | Severity | Result | Note |
|---|---|---|---|
| `no_currency_terms` | high | ✅ | No dollar signs or computed revenue figures |
| `no_product_store_root_cause` | high | ✅ | Root cause does not name products or stores |
| `evidence_non_empty` | medium | ✅ | 14 evidence items in ledger |
| `headline_non_empty` | medium | ✅ | Headline produced |
| `confidence_calibration` | medium | ✅ | `medium` confidence, 1 round, 5 gaps — calibrated correctly |
| `unknowns_when_thin_evidence` | low | ✅ | Unknowns section populated |
| `external_not_sole_source` | medium | ✅ | No external evidence used as primary source |
| `monitoring_plan_populated` | low | ✅ | Monitoring plan has concrete metrics |

**Deterministic score: 1.0 (8/8 passed)**

---

## Stage 6 — Alignment Reviewer (LLM judge, deep model)

**What it does:** Grades the `DecisionBrief` against the project's guardrails and usefulness criteria. Produces a 0–1 alignment score.

**System prompt:**
```
You are a quality reviewer for retail RCA outputs.
Core guardrails (hard rules):
1. City/date grain only — no product or store IDs in root cause claims.
2. No dollar signs or computed revenue figures.
3. Internal facts are primary; external is supportive only.
4. Confidence calibrated to evidence volume. High confidence requires substantial evidence.
5. "Insufficient evidence" is a valid outcome — do not force a root cause.

Usefulness criteria (soft rules):
6. Recommended action must be specific and actionable for the named owner function.
7. Monitoring plan must specify concrete metrics, not vague outcomes.
8. Evidence claims must be traceable — not fabricated from the signal alone.
9. Caveats must acknowledge data limitations honestly.

Return ONLY valid JSON:
{
  "alignment_score": <float 0.0–1.0>,
  "alignment_label": "aligned|partial|misaligned",
  "pros": [...], "cons": [...], "improvements": [...],
  "comment": "<one sentence>"
}
Scoring: aligned 0.75–1.00 | partial 0.40–0.74 | misaligned 0.00–0.39
```

**Reviewer verdict:**
```json
{
  "alignment_score": 0.90,
  "alignment_label": "aligned",
  "comment": "The brief correctly diagnoses a baseline artefact rather than forcing a demand narrative, but the headline uses 'Dragon Boat Festival Sunday' without flagging it as inferred.",
  "pros": [
    "Correctly distinguishes baseline conflict from real demand drop — avoids false alarm.",
    "Recommends specific, actionable baseline recalibration within Planning & Analytics remit.",
    "Honest about unlabeled activity_flag and inferred holiday name in caveats.",
    "Monitoring plan lists concrete, trackable metrics and a clear escalation trigger."
  ],
  "cons": [
    "Headline uses 'Dragon Boat Festival Sunday' unqualified — caveats say holiday name is inferred.",
    "Moderate weather named as equally likely cause in headline, but treated as minor factor in body."
  ]
}
```

The LLM judge and the deterministic audit disagree on the headline hedging — the 8 checks passed (no specific check for headline qualifier phrasing), but the judge caught the inconsistency. This is the value of running both layers.

---

## Stage 7 — Memory Distiller

**What it does:** Extracts 3–5 reusable lessons from the final report. Written to `rca.memory` for future city 0 runs.

**System prompt:**
```
Write short reusable city lessons from one RCA run.
Return markdown with section ## Lessons and 3-5 bullets.
Only extract lessons directly supported by evidence — do not generalize beyond this run.
```

**User message:** the full `final_report` markdown.

**Lessons written to `rca.memory`:**
```markdown
## Lessons

- Same-weekday-4w baseline is unreliable during holiday periods — prior Sundays
  may include pre-festival peaks that inflate the reference point. Always compare
  against the 7-day rolling baseline as a sanity check before treating a holiday
  signal as a real drop.

- More aggressive discounting on a drop day did not compensate for the demand
  shortfall — if discount depth increased but sales still fell vs baseline,
  the issue is likely demand or baseline artefact, not price.

- Higher stockout rates (39.6%) on the festival day vs the prior lift day (31.1%)
  suggest supply may have constrained demand. Consider velocity-weighted stockout
  analysis before concluding a drop was purely demand-side.
```

These lessons are stored with `influence_score: 0.5`. The next run for city 0 will receive all these plus the May 1 lessons — so the planner already knows to sanity-check the 4-week baseline against the rolling average before treating a holiday signal as a real drop.

---

## End-to-End Summary

```
Stage 0   Signal trigger (no LLM)
          28,147 sales, -18.6% vs 4-week Sunday baseline → signal fires

Stage 1   Planner (fast model, 1 LLM call)
          Prior memory loaded. Select 6 agents.
          Objective: baseline artefact or real demand drop?

Stage 2   6 agents in parallel (fast model, ~2-3 tool rounds each)
          Key finding: +6.6% vs 7-day baseline contradicts the -18.6% signal.
          Deeper discounting on drop day did not compensate.
          Stockouts higher than lift day.

Stage 3   Critic (fast model, 1 LLM call)
          5 gaps identified. Confidence ceiling: medium.
          continue_investigation = false → loop exits after 1 round.

Stage 4   Coordinator (deep model, 1 LLM call)
          Brief: baseline artefact, not demand collapse.
          Recommended action: recalibrate baseline for holiday periods.
          Owner: Planning & Analytics.

Stage 5   8 deterministic checks (no LLM)
          Score: 1.0 — all pass.

Stage 6   LLM judge (deep model, 1 LLM call)
          Score: 0.90 — aligned. Flags headline hedging inconsistency.

Stage 7   Memory distiller (fast model, 1 LLM call)
          3 lessons written to rca.memory for future city 0 runs.

Stage 8   Record node
          Everything persisted to Supabase (outcomes, events, completions,
          memory, evidence_cache).
```

**Total LLM calls:** ~17
- Planner: 1
- 6 specialists × ~2 tool rounds each: ~12
- Critic: 1
- Coordinator: 1
- LLM judge: 1
- Memory distiller: 1
