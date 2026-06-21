# ADR 0003: Level 5 Learning-Mode Agentic RCA

## Status

Implemented across three phases (Phase 1: commit 272598d, Phase 2: commit 7eecff7, Phase 3: this commit).

## Context

ADR 0002 defined the direction: replace the flat parallel planner/specialist/critic/coordinator graph with a bounded autonomous investigation loop. This ADR records the concrete decisions made while implementing that upgrade as the "Level 5 Learning-Mode" system.

The key constraint driving every decision is the data grain: all runtime evidence is city/date only. Agents may suggest product or store follow-up as unavailable data, but must not claim product/store root causes.

## Phase 1 — Enhanced Signal Layer and Schema

### Decisions

- Extended `rca.outcomes` with JSONB columns: `decision_brief_json`, `evidence_ledger_json`, `investigation_rounds_json`, `critic_reviews_json`, `monitoring_plan_json`, `evaluation_json`, `memory_context_json`, and added `round_count integer`.
- Added `memory_json jsonb` and `influence_score float` to `rca.memory` to carry structured lessons alongside free-text.
- Added `rca.external_events` table to cache news search results keyed by city/date/query.
- Added structured Pydantic v2 models to `rca/state.py`: `EvidenceItem`, `CriticGap`, `CriticReview`, `InvestigationRound`, `DecisionBrief`, `MonitoringPlan`, `DeterministicCheck`, `LlmJudgeResult`, `EvaluationResult`, `MemoryInfluence`, `RcaRunState`.

### Why

JSONB columns let the schema evolve without a migration for every agent output change. Stable filtering and preview columns (city_id, dt, signal_label, confidence, headline) stay as typed SQL columns for dashboard queries. Everything else lives in JSONB.

## Phase 2 — Bounded Investigation Loop

### Decisions

**Graph restructured** to `START → investigation_loop → decision → evaluation → memory → record → END`. The investigation loop is a Python function, not a LangGraph subgraph, to keep the bounded-loop logic explicit and testable without graph machinery.

**Investigation loop** runs up to `RCA_MAX_INVESTIGATION_ROUNDS` rounds (default 5). Each round:
1. Planner selects agents and returns a `PlannerDecision` (selected_agents, objective, target_gaps, expected_evidence).
2. Selected agents run in parallel via `ThreadPoolExecutor`.
3. Each agent result is converted to `EvidenceItem` objects (one `observation` per tool call, one `inference` per memo).
4. Critic returns a structured `CriticReview` JSON with `continue_investigation`, `confidence_ceiling`, `gaps`, and `stop_reason`.

**Three stop conditions** (all must be false for the loop to continue):
1. Critic's `continue_investigation` is `False`.
2. Critic identified gaps but all have `gap_type == "unavailable_data"` (empty gaps list does not trigger this stop — empty means "no specific direction but keep going").
3. Max rounds reached.

**Repetition guard** prevents re-running the same agent against the same gap targets in the same run. Key: `agent_name__initial` (no gaps) or `agent_name__sorted_gap_ids`.

**news_agent gating**: Only dispatched when (a) `RCA_RESEARCH_ENABLED=true`, (b) at least one internal evidence item exists, and (c) critic identified a `missing_external_context` gap. Never in round 1.

**Structured critic**: Critic prompt requires JSON output. Fallback on parse error is a conservative stop (continue=false) rather than an optimistic continue.

**DecisionBrief**: Coordinator returns a structured JSON matching the `DecisionBrief` Pydantic model. `_brief_to_markdown()` renders it into three named sections: `## RCA`, `## Prediction`, `## Prescription`.

### Why these choices

- Bounded Python loop is simpler to test and debug than a LangGraph conditional edge loop.
- Structured critic JSON makes the stop decision deterministic and auditable.
- Evidence ledger gives the evaluation node traceable items to count and classify.
- Parallel agent dispatch per round keeps latency bounded without sacrificing coverage.

## Phase 3 — Evaluation, Gated Tools, and Audit Checks

### Decisions

**Eight deterministic audit checks** in `rca/audits.py`, applied by `run_evaluation()` after the decision node:

| Check | Severity | Rule |
| --- | --- | --- |
| `no_currency_terms` | high | No `$`, USD, CNY, or computed revenue/profit/margin with numbers |
| `no_product_store_root_cause` | high | No product/SKU/store identifiers in causal claims |
| `evidence_non_empty` | medium | At least 1 evidence item in the ledger |
| `headline_non_empty` | medium | Non-empty, non-fallback headline |
| `confidence_calibration` | medium | High confidence requires ≥5 inference items; medium requires ≥2 |
| `unknowns_when_thin_evidence` | low | Fewer than 3 evidence items requires non-empty unknowns list |
| `external_not_sole_source` | medium | At least one non-external evidence item must exist |
| `monitoring_plan_populated` | low | `metrics_to_watch` must be non-empty |

**Scoring**: Start at 1.0. Each failed check deducts `high=-0.25`, `medium=-0.10`, `low=-0.05`. `passed = score >= 0.5`.

**`run_stat_analysis` gated tool** in `rca/tools.py`:
- Requires non-empty `rationale` and `decision_use` fields before executing computation.
- Three methods: `robust_baseline_check` (same-weekday baseline), `driver_shift_scan` (intraday shape comparison), `simple_expected_sales_sanity_check` (signal deviation sanity).
- Gated by `RCA_STAT_TOOLS_ENABLED=true` (default).
- Added to statistician's `tool_names`.

**Optional LLM judge** wired as `LlmJudgeResult(enabled=False)` by default. Controlled by `RCA_LLM_JUDGE_ENABLED` (default false). The `EvaluationResult` schema already has all six judge dimensions (`groundedness`, `calibration`, `actionability`, `management_usefulness`, `scope_discipline`, `restraint`) for future wiring.

### Why these choices

- Deterministic checks catch hard constraint violations (currency, product/store scope) before they reach the dashboard or a human decision-maker.
- The score gives a single number useful for regression tracking across runs.
- Gated stat tools require the agent to articulate why the analysis is needed — this prevents blind tool use and keeps the tool call auditable.
- LLM judge stays off by default; the cost of an LLM evaluation call per RCA run is not justified at the current scale.

## Invariants that must not change without a new ADR

- Runtime grain stays at city/date. No product or store identifiers in root cause claims.
- `sale_amount` and `hours_sale` are normalized, not currency. No dollar signs, USD, or CNY in output.
- External evidence is supportive only. Internal Supabase facts remain the primary source.
- The agent must say "insufficient evidence" rather than force a cause.
- `SUPABASE_SERVICE_ROLE_KEY` is backend only; never exposed to the browser.
