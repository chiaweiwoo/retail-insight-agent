# Improvement Plan — Calibrated RCA, v2 (cloud + LangGraph)

> **Planned on Opus. Execute on Sonnet (or Gemini Pro).** Learning project, rollback-safe.
> This file is both an execution plan **and** a learning artifact.
> **Executes in 3 rounds, max.** Each round ends in a working, committed, deployable state.
> Delete scratch docs at the very end; keep README, PRD, CLAUDE.md, AGENTS.md.

---

## HANDOFF — Current state as of 2026-06-20 (start here)

**Branch**: `redesign/calibration-first` | **Last commit**: `06140eb feat(reflect): add bounded reflection node`

Phases 1.1–2.6 are complete and green. Remaining: **2.7 → 2.8 → 3.1 → 3.2 (PAUSE) → 3.3 → 3.4 → 3.5**.

### Invariants that apply to every remaining phase

- Run `uv run python -m rca.cli run --store h555 --dt 2024-05-16 --dry-run --full` as the smoke gate before each commit — must complete with no exceptions.
- Commit + push after each phase. Check CI: `gh run list --limit 1` — wait for green.
- Never run SQL directly. Author a migration file; user runs it in the Supabase SQL Editor.
- `sale_amount` / `hours_sale` are normalized coefficients, not currency. Never emit `$` or "revenue".
- Store prefix groups (`h/m/l`) are opaque IDs — do not call them "tiers".
- Peer comparisons come from a 15-store local sandbox — always note the small-sample limitation.
- Prompt changes (any `*_PROMPT` constant) → run `/prompt-audit` before committing.

### Key files — what exists now

| File | Status | Role |
|------|--------|------|
| `rca/graph.py` | NEW (Phase 2.1) | LangGraph `StateGraph`; `run_rca_graph()` is the main entry point |
| `rca/obs.py` | NEW (Phase 2.4) | Langfuse tracing wrapper; no-ops silently when env keys are absent |
| `rca/profiles.py` | NEW (Phase 2.5) | Episodic store memory: `get_store_profile`, `distil_store_profile`, `reset_store_profile` |
| `rca/llm.py` | MODIFIED | Added `NODE_MODEL_MAP`, `make_routed_settings()`, `ClientFactory` type alias |
| `rca/agents.py` | MODIFIED | All private `_run_*` functions accept `profile_text: str \| None = None` |
| `rca/context.py` | MODIFIED | `build_context_preamble(store_alias, dt, pack, profile_text)` — injects store memory |
| `rca/evaluator.py` | TO MODIFY (2.7) | Currently 5 judge dimensions; Phase 2.7 adds 4 more + free-text verdict |
| `rca/mcp_server.py` | TO CREATE (2.8) | FastMCP server exposing read-only tools |
| `rca/stubclient.py` | MODIFIED | Has stubs for all nodes incl. `"reflect"` and `"evaluator"` (5-field JSON today) |
| `rca/tools.py` | EXISTS | All read-only query functions used by specialist agents |
| `rca/cli.py` | MODIFIED | `rca distil`, `rca reset-memory`, `rca run --reflect` added |
| `rca/bench.py` | MODIFIED | Imports and calls `run_rca_graph` (not `run_coordinator`) |

### Architecture summary

**Graph nodes** — lowercase_underscore names must match keys in `NODE_MODEL_MAP` in `rca/llm.py`:

```
START → plan → [Send fan-out] → run_specialist (×N parallel)
     → critic → synthesize → controller → slt
     → [conditional: enable_reflection?] → reflect? → sanitize
     → record → artifacts → END
```

**Config injection** — every node callable receives `config: RunnableConfig`. Extract via:
```python
from langchain_core.runnables import RunnableConfig
cfg = config.get("configurable", {})
settings: LLMSettings      = cfg["settings"]
client_factory: ClientFactory = cfg["client_factory"]
logger: RunLogger          = cfg["logger"]
observer: RcaObserver      = cfg["observer"]
is_dry_run: bool           = cfg["is_dry_run"]
```

**Model routing** — call `make_routed_settings(base_settings, node_name)` before each LLM call to get the right model. Fast tier = `DEEPSEEK_MODEL_FAST` env var; deep tier = `DEEPSEEK_MODEL_DEEP`.

**Dry-run contract** — pass `client_factory=stub_client_factory` from `rca/stubclient.py`. Every node that calls an LLM **must** have an entry in `_STUB_RESPONSES`. The `"evaluator"` entry must be a JSON string parseable by `json.loads()`.

**Tools available** (in `rca/tools.py`):
`get_signal_evidence`, `get_sales_context`, `get_stockout_context`, `get_stockout_baseline`,
`get_discount_context`, `get_activity_context`, `get_calendar_weather_context`,
`get_peer_store_context`, `get_prior_rca`, `get_tool_schemas`

**Supabase** — all reads/writes via `supabase-py` client in `rca/db.py`. Tables in `public` schema with `rca_` prefix. Service role key is backend-only; never send it to the frontend or check it into git.

---

## Phase 2.7 — Evaluator: executive-usefulness judge

**File**: `rca/evaluator.py`

`EVALUATOR_SYSTEM_PROMPT` currently scores 5 dimensions. Extend it to score 9 and return a free-text verdict.

**New dimensions** (1–5 each):
- `time_to_decision`: can the SLT decide within one read without chasing footnotes?
- `format_compliance`: does the card have all 6 required fields (headline / confidence / materiality / pattern / action / escalate)?
- `procedure_transparency`: can a reader tell which analysts ran, what the critic changed, and why?
- `restraint`: does the output avoid over-claiming, inventing data, or asserting causal links without evidence?

**New free-text field**:
- `executive_pov` (string): "Would I act on this? What's missing?" — one paragraph, plain language.

Updated prompt must instruct: return valid JSON with exactly these 9 numeric keys + 1 string key:
`groundedness, calibration, actionability, conciseness, causal_honesty, time_to_decision, format_compliance, procedure_transparency, restraint, executive_pov`

Update `_render_eval_markdown` to add the 4 new numeric columns to the table and print `executive_pov` as an indented line beneath each scenario row.

Update `_STUB_RESPONSES["evaluator"]` in `rca/stubclient.py` to include all 10 fields:
```python
"evaluator": '{"groundedness": 4, "calibration": 4, "actionability": 3, "conciseness": 4, "causal_honesty": 4, "time_to_decision": 3, "format_compliance": 5, "procedure_transparency": 4, "restraint": 4, "executive_pov": "Stub evaluation only."}',
```

**Checkpoint**: `uv run python -m rca.cli eval --dry-run` shows new columns in `eval_report.md`; `uv run pytest` green; dry-run smoke green.

---

## Phase 2.8 — MCP server

**File to create**: `rca/mcp_server.py`
**Dependency**: `fastmcp>=2.0` — already in `pyproject.toml` (confirmed installed).

Pattern using FastMCP 2.x:
```python
from fastmcp import FastMCP
from rca.tools import (
    get_signal_evidence, get_sales_context, get_stockout_context,
    get_stockout_baseline, get_discount_context, get_activity_context,
    get_calendar_weather_context, get_peer_store_context, get_prior_rca,
)

mcp = FastMCP("retail-rca")

@mcp.tool()
def signal_evidence(store_alias: str, dt: str) -> dict:
    """Get signal evidence for a store on a given date.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_signal_evidence(store_alias, dt)
```

Wrap all 9 tool functions listed above. Each docstring **must** include the data caveats (normalized sales, small-sample peer groups, opaque store IDs).

Add `rca mcp` CLI command in `rca/cli.py`:
```python
def _cmd_mcp(args) -> None:
    from rca.mcp_server import mcp
    mcp.run()

# in main(), alongside other subparsers:
sub = subparsers.add_parser("mcp", help="Launch MCP tool server (read-only)")
sub.set_defaults(func=_cmd_mcp)
```

**Checkpoint**: `uv run python -m rca.cli mcp --help` exits cleanly; dry-run smoke unaffected; `uv run pytest` green.

---

## Phase 3.1 — Next.js dashboard (local first)

**Directory**: `dashboard/` (create from scratch in the repo root).

**Stack**: Next.js 14+ (App Router) · TypeScript · Tailwind CSS · Tremor (charts) · `@supabase/supabase-js`

**Scaffold**:
```bash
pnpm create next-app dashboard --typescript --tailwind --app --src-dir --import-alias "@/*" --no-eslint
cd dashboard && pnpm add @supabase/supabase-js @tremor/react
```

**Supabase client** at `dashboard/src/lib/supabase.ts`:
```ts
import { createClient } from '@supabase/supabase-js'
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
)
```

**`dashboard/.env.local`** (gitignored; user fills in after Vercel project is created):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

**Pages** (App Router — all under `dashboard/src/app/`):

| Route | File | Content |
|-------|------|---------|
| `/` | `page.tsx` | Store list — signal status badges (drop / lift / none); filter by city |
| `/stores/[storeId]` | `stores/[storeId]/page.tsx` | Sales time series (Tremor AreaChart); triggered dates marked; descriptive stats (mean, stddev, weekday pattern) |
| `/stores/[storeId]/rca` | `stores/[storeId]/rca/page.tsx` | Decision cards list (confidence + escalate badges); click to expand report / critique / story markdown |
| `/stores/[storeId]/profile` | `stores/[storeId]/profile/page.tsx` | Distilled store profile + recurrence counts (from `rca_store_profile`) |

All reads use the **anon key under RLS** — anon SELECT is allowed on dim/fact/signal/outcome/profile tables; no write paths exist in the dashboard. Surface the small-sample caveat on the peer view.

**`dashboard/.env.local.example`** (commit this file with blanks; `.env.local` stays gitignored).

**Checkpoint**: `pnpm dev` in `dashboard/` renders against Supabase; `pnpm build` succeeds with no TS errors.

---

## Phase 3.2 — Deploy to Vercel  ← PAUSE (user action required)

**PAUSE** — user must do all of this before the agent continues:
1. Go to vercel.com → New Project → import the GitHub repo → set **Root Directory** to `dashboard/`
2. In Project → Settings → Environment Variables, add:
   - `NEXT_PUBLIC_SUPABASE_URL` (from Supabase Project Settings → API → Project URL)
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY` (from Supabase Project Settings → API → anon key)
3. Trigger the first deploy
4. Confirm the deployed URL loads and reads data
5. Verify RLS: the anon key can SELECT from tables but cannot INSERT/UPDATE/DELETE

After user confirms, agent adds `dashboard/vercel.json` if needed and confirms the build settings are correct.

---

## Phase 3.3 — Skills

**File to create**: `.claude/skills/rca-story/SKILL.md`

This is a Claude Code skill file (Markdown). Content should describe the procedure for regenerating a reader-facing story report for a completed run:

```markdown
# Skill: rca-story

Regenerate the reader-facing story report for a completed RCA run.

## When to use
The user says "generate story for <run_folder>" or "write the story report for <store> <date>".

## Steps
1. Locate the run folder under `data/analysis/agent_benchmark_runs/<run_folder>/`
2. Run: `uv run python -m rca.cli story --run-dir data/analysis/agent_benchmark_runs/<run_folder>`
3. Output is written to `output/story_reports/<run_folder>/`
4. Read and summarise the story report for the user.

## Grounding rules
- Do not invent drivers not present in the coordinator trace.
- Do not claim certainty beyond what the decision card confidence field states.
- Normalized sales figures are coefficients, not currency.
```

Optionally add `.claude/skills/rca-run/SKILL.md` for an end-to-end run + card summary workflow.

---

## Phase 3.4 — Documentation

**All files require a conflict pass**: re-read the whole file, resolve contradictions, then write. Stale docs are worse than no docs.

### `README.md` — rewrite as Agents 101 (§E outline below)

1. What this is + ASCII funnel diagram (label each step: code vs LLM)
2. Components at a glance — table: Agent | Tools | Model | When | What it must change
3. How an LLM agent works — system prompt, tools, ReAct loop (worked example), parallel specialists
4. Why critic + coordinator + decision card — the funnel logic; calibration; confidence-led
5. Staying honest — faithfulness check, LLM-as-judge ≠ critic, small-sample caution, no currency
6. Memory over time — episodic vs semantic, distillation, store profile, `rca replay` / `rca reset-memory`
7. Model routing — cheap/strong table + cost rationale
8. The ecosystem — LangGraph, MCP, Skills, Langfuse, Supabase, Vercel (one sentence each: what it is + how to run)
9. Glossary (the concept table from §2 of this plan, expanded)
10. Full CLI command list (all `rca *` subcommands)
11. Data (minimal) — Supabase tables, the raw parquet source, the 15-store local sandbox vs 5-city full scope

### `AGENTS.md` — conflict pass + these additions
- Replace old orchestration description with LangGraph pipeline + `RcaState` fields
- Tool table: add `get_stockout_baseline`; update all descriptions to reference Supabase (not DuckDB)
- Add **Dashboard section** matching Phase 3.1 page/route spec above
- Move MCP and Skills from "Out of Scope" to a shipped-features section
- Update scope framing from "single city / 15 stores" to "15-store local sandbox; 5-city full dataset"

### `CLAUDE.md` — conflict pass + these additions
- New commands: `rca distil [--store ALIAS] [--dry-run]`, `rca reset-memory [--store ALIAS | --all]`, `rca run --reflect`, `rca mcp`
- Datastores section: `data/rca.duckdb` (ETL only); `data/runs.duckdb` (legacy); Supabase is system of record
- Routing: specialists → fast model; synthesis/oversight → deep model
- Deterministic sanitizer: no LLM calls in sanitize; runs once at write boundary

### `PRD.md` — update scope and roadmap
- Mark all Round 1 + Round 2 items as shipped
- Dashboard and Vercel deploy as current/in-progress
- Remove any future-tense items that are now complete

### Delete
`docs/REDESIGN_PLAN.md` (if it exists) and any other scratch markdown files. Keep: `README.md`, `PRD.md`, `CLAUDE.md`, `AGENTS.md`.

**Checkpoint**: a fresh reader can answer "what are the agents, their tools, when each runs, where the LLM helps, and how to run/deploy it" from README alone; no doc contradicts shipped behavior.

---

## Phase 3.5 — Land it

1. Delete `docs/IMPROVEMENT_PLAN.md` (this file)
2. Final live smoke: `uv run python -m rca.cli bench` → `uv run python -m rca.cli eval --run-dir <bench_dir>` → open Vercel URL
3. Commit, push, `gh run list --limit 1` — confirm green

---

---

## 0. Decisions locked with the user

| Decision | Choice |
| --- | --- |
| Data scope | **Curated multi-city: top 5 cities by store count** (city 0, 12, 3, 13, 16 ≈ 677 stores), store-day grain. Fixes the single-city bias with real peer groups. Category drilldown deferred (raw supports it later). |
| Agent framework | **Re-platform onto LangGraph** (explicit state graph). The headline learning piece. |
| Dashboard | **Next.js on Vercel**, reading Supabase (matches `tcm-diagnosis`). |
| Observability | **Adopt Langfuse** — trace every LLM call; back the LLM-as-judge eval. |
| Database | **Supabase (Postgres), schema `retail_rca`, RLS on.** Replaces both DuckDB files as the system of record. DuckDB stays only as a local ETL/compute engine for the raw parquet. |
| Models | DeepSeek. `DEEPSEEK_MODEL_FAST=deepseek-v4-flash`, `DEEPSEEK_MODEL_DEEP=deepseek-v4-pro` (confirmed from `tcm-diagnosis`). Route hard nodes → pro. |
| Libraries-first | Do **not** hand-roll what a mature library does: LangGraph (orchestration), Pydantic (typed/structured output), Langfuse (observability), official MCP SDK / FastMCP (tool server), `supabase-py` (DB client), Next.js + Tremor/Recharts + Supabase JS (dashboard). |

---

## 1. Principles (locked)

1. **Calibration is the product, not the prose.** Confidence is structured and propagated end to end.
2. **Every node must change the output.** No agent theater.
3. **Evidence-first; never fabricate.** Every claim traces to a tool number. No invented margin/currency.
4. **Every stage is inspectable.** Walk the trace (now also Langfuse) to the node that caused a wrong card.
5. **Small sample, distrust comparison.** Even multi-city, this is a sampled subset. Peer/fleet reads are
   priors, not root causes. External (web) context can *add* bias. Down-weight when unsure.
6. **Spend tokens where reasoning is hard.** Deterministic code or the cheap model for mechanical work;
   the pro model only for genuine synthesis and judgment. Cost stays roughly flat.
7. **(NEW) Cloud-honest.** Secrets never in code or git. RLS on every table. The dashboard reads with an
   anon key constrained by RLS; the backend writes with the service key. The user owns all provisioning;
   the agent pauses and asks at each setup boundary.

### Checkpoint discipline (every phase)

GREEN only when ALL pass; never proceed on red (fix or `git restore`). Commit per green phase.
1. `uv run python -c "import rca"` succeeds.
2. Targeted tests + full `uv run pytest` green.
3. **Dry-run smoke** (pipeline phases): `rca run --store <s> --dt <d> --dry-run --full` completes on the
   stub client (no API, no network), expected artifacts present.
4. **Trace sanity**: every node logged an input and output; new nodes appear.

Stub-client dry-run is the per-phase gate (free, deterministic). A **live smoke** (one real run) runs once
at the end of each round. **Supabase/Langfuse/Vercel reads in dry-run are mocked** so checkpoints never need
the network.

---

## 2. Concept primer (the vocabulary the README will teach)

| Term | Meaning | Where |
| --- | --- | --- |
| **Agent** | LLM + role (system prompt) + tools + goal, acting in a loop. | each LangGraph node |
| **Tool** | A plain function returning real data (read-only Supabase queries). | `rca/tools.py` |
| **ReAct loop** | Reason → Act (tool) → Observe → repeat → answer. | specialist nodes |
| **LangGraph** | A library to define agents as an explicit **state graph** (nodes + edges + shared state). | `rca/graph.py` (new) |
| **State** | The typed object passed along the graph (store, dt, memos, critic note, card…). | `RcaState` (Pydantic) |
| **Planner / conditional edge** | Cheap logic choosing which specialist nodes run. | `plan_specialists` → graph edges |
| **Critic / reflection** | One bounded review pass that downgrades claims. | critic node |
| **Bounded reflection** | One targeted re-check when a claim is uncalibrated. | optional reflect node |
| **LLM-as-judge** | A separate LLM scoring quality offline; never edits the run. | `rca/evaluator.py` |
| **Faithfulness check** | Non-LLM: cited numbers must appear in tool outputs. | `deterministic_faithfulness_check` |
| **Model routing / cascade** | Cheap vs strong model per node by difficulty. | `rca/llm.py` + map |
| **Grounding / context pack** | Small factual brief injected into prompts. | `rca/context.py` |
| **Episodic memory** | Log of past run outcomes (one row per run). | `rca_outcome` table |
| **Semantic / profile memory** | Distilled, evolving per-store summary. | `store_profile` table |
| **Distillation / consolidation** | Rolling episodes into a compact profile. | `rca distil` |
| **Observability (Langfuse)** | Traces/cost/latency for every LLM call. | `rca/obs.py` wrapper |
| **MCP** | A server publishing tools to any MCP client. | `rca/mcp_server.py` |
| **Skill** | A saved playbook (`SKILL.md`) Claude can invoke. | `.claude/skills/` |
| **RLS** | Row-Level Security — Postgres policies controlling who reads/writes each row. | Supabase migrations |

**Mental model:** a **tool** is a function; an **agent** is an LLM deciding when to call tools; **LangGraph**
wires agents into a graph; **MCP** publishes the tools to other apps; a **skill** is a saved procedure;
**Langfuse** records what every LLM call did; **Supabase** is where all the data lives.

---

## 3. Problems carried over (still fixed, now inside the new platform)

- LLM sanitizer fired ~20–25×/run ([report.py:1009]) → make deterministic + one optional final polish.
- `rca eval` silently scores nothing ([evaluator.py:147]) → fix resolver + raise on zero.
- Currency invented from normalized data (controller `$28K`) → forbid; size materiality relatively.
- Peer over-indexing unverified/ amplified by critic → enforce small-sample caution + verify.
- Reports beg for a stockout baseline the DB has → add `get_stockout_baseline`.
- `find_report_language_issues` gates nothing → wire as a test.
- Stale README DAG (no critic/controller/slt) → rebuilt in Round 3.

---

## 4. Target architecture (after all 3 rounds)

```
SUPABASE (schema retail_rca, RLS on)
  dims + 4 fact tables (store-day, 5 cities) | signals | rca_outcome | store_profile | run_log
        ▲ writes (service key)                                   ▲ reads (anon + RLS)
        │                                                        │
  BACKEND (Python, uv, LangGraph)                          NEXT.JS DASHBOARD (Vercel)
  build: DuckDB aggregates raw parquet → upsert to Supabase     time-series + triggers
  run:  LangGraph state graph                                   precomputed RCA cards + drilldown
    context_pack + store_profile  (grounding)                   store profile / memory view
      → plan (conditional edges)                                signal grid + filters
      → specialists ∥ (ReAct, Pydantic Assessment)
      → critic (small-sample caution)
      → [reflect?]  → coordinator → finance_controller → slt_brief (card)
      → record outcome → (periodic) distil → store_profile
    every LLM call traced to LANGFUSE; routed cheap/strong by node
  publish: MCP server (read-only tools) | skills (story/run playbooks)
  offline: evaluator (LLM-as-judge incl. EXEC USEFULNESS + faithfulness gate + signal check)
```

---

# ROUND 1 — Data + Supabase + correctness (backend, current orchestration)

**Outcome of the round:** multi-city data in Supabase with RLS; the existing pipeline reads from Supabase;
sanitizer/eval/currency/peer-bias fixed; the stockout-baseline tool added. A correct, cloud-backed system
*before* we touch orchestration. (We fix prompts/tools/report/eval here — all of which carry into LangGraph
unchanged — so Round 2 doesn't redo this work.)

### Phase 1.1 — Dependencies + env scaffolding
- Add deps (`uv add`): `supabase`, `pydantic>=2`, `python-dotenv` (if not present). (LangGraph/Langfuse
  come in Round 2.)
- Create `.env.example` mirroring the sibling repos (see §A). Backend keys only this round:
  `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_DB_SCHEMA=retail_rca`, `DEEPSEEK_API_KEY`,
  `DEEPSEEK_MODEL_FAST`, `DEEPSEEK_MODEL_DEEP`.
- **[PAUSE 1 — YOU DO]:** create a free Supabase project; from Project Settings → API copy the **Project
  URL**, **anon key**, **service_role key**; from Settings → Database copy the **connection string**
  (we use the service key via `supabase-py`, not a raw connection, per your rule). Paste URL +
  service_role into `.env`. Tell me when done.
- _Checkpoint:_ import ok; `.env.example` committed; pytest green.

### Phase 1.2 — Supabase schema + RLS migration (you apply the SQL)
- Author `supabase/migrations/0001_init_retail_rca.sql` (see §B for the full schema): `CREATE SCHEMA
  retail_rca`; dim + 4 fact tables; `signals`; `rca_outcome`; `store_profile`; `run_log_event`. Add
  indexes on `(store_id, dt)`.
- Author `supabase/migrations/0002_rls.sql`: `ENABLE ROW LEVEL SECURITY` on every table; **anon SELECT**
  policies on the read tables the dashboard needs; **no** anon insert/update/delete (service key bypasses
  RLS for the backend). This satisfies the Supabase security advisor.
- **[PAUSE 2 — YOU DO]:** open Supabase → SQL Editor, run `0001` then `0002` (or approve me applying them
  via the Supabase MCP). Run `get_advisors` (security) and confirm no "RLS disabled" warnings. Tell me when
  green.
- _Checkpoint:_ migrations committed; you confirm tables exist + RLS on.

### Phase 1.3 — Multi-city ingestion (DuckDB ETL → Supabase upsert)
- Rewrite `rca/database.py` build path: DuckDB reads `data/raw/train.parquet`, **filters to the 5 chosen
  cities**, aggregates to store-day fact tables + dims (same shape as today), computes `signals`
  (reuse `signals.py`), then **upserts to Supabase via `supabase-py`** in chunks (~1–2k rows/request).
  No raw DB connection; client only.
- Add `CITY_IDS = (0, 12, 3, 13, 16)` to config; drop the hardcoded 15-store `STORE_MAP` (store_id is now
  the real key; aliases become opaque `c{city}_s{store}` or just `store_id`). Update `EXPECTED_*` counts to
  be computed, not constants.
- Rewrite `rca/evidence.py` + the read paths in `rca/tools.py` to query Supabase (client `.select()` on
  tables/views) instead of DuckDB. Heavy analytical shaping that PostgREST can't express goes into a
  Postgres **view or RPC** defined in a migration (`0003_views.sql`) and called via the client.
- Keep a `--local-duckdb` escape hatch only if cheap; otherwise Supabase is the one source of truth.
- _Checkpoint:_ `rca build` ingests 5 cities; a read test (e.g. `get_signal_evidence`) returns the same
  numbers the DuckDB path produced for a spot-checked store-day; pytest green. **[PAUSE if row counts look
  off — show me before proceeding.]**

### Phase 1.4 — Deterministic report build + one optional polish
- Make `sanitize_generated_markdown` ([report.py:1009]) **pure deterministic** (regex/string: units/
  revenue→"sales amount"; `$<n>`→"<n> sales amount"; tier→"store group"; mojibake via `_repair_mojibake`).
  No network.
- Remove redundant sanitize calls in nodes ([agents.py:385,515,565,613,665]) and the re-sanitize block
  ([agents.py:793-798]); sanitize **once** per artifact at the write boundary so `.md` and `.html` match.
- Add optional `polish_final_report(...)` LLM pass on final artifacts only, behind `--polish` (default off).
- Wire `find_report_language_issues` into a test (zero forbidden strings on dry-run output).
- _Checkpoint:_ dry-run shows no sanitizer LLM calls in the run log; language test passes; pytest green.

### Phase 1.5 — Currency + small-sample (multi-city) guardrails
- `finance_controller` prompt: values are **normalized coefficients**; size materiality **relatively**
  (% of fleet, multiples of store-normal); **never** emit `$`/currency.
- `market_analyst` + `critic` prompts: peers are now real (multi-city) but still a **sampled subset** —
  treat peer/fleet as a prior, not a root cause; critic must **down-weight**, not amplify, peer-only claims.
- `research_analyst`/`coordinator`: external/web context is a weak prior that can add bias.
- Update CLAUDE.md + AGENTS.md scope text from "single city / 15 stores" → "5-city sample" (conflict pass).
- _Checkpoint:_ dry-run green; a live re-run of `m041 2024-05-09` (or a new multi-city drop) shows tempered
  peer language + no currency; pytest green.

### Phase 1.6 — Self-calibration tool
- `get_stockout_baseline(store_id, dt, window=30)` in `tools.py` (trailing-N avg + stddev + z-score),
  backed by a Supabase view/RPC. Grant to `ops_analyst`; prompt must compare day-vs-baseline (no more punt).
- Stub client: canned baseline response.
- _Checkpoint:_ unit test vs hand SQL; dry-run ops memo cites baseline; pytest green.

### Phase 1.7 — Eval fix + faithfulness gate (signal/groundedness only this round)
- Fix `_resolve_scenario_dirs`/`_cmd_eval` (accept single-run or bench layout; **raise** on zero scenarios).
- Promote `deterministic_faithfulness_check` to a surfaced gate (top of `eval_report.md`; optional non-zero
  exit). (The exec-usefulness judge + Langfuse-backed judging land in Round 2.)
- Refresh benchmark scenarios to multi-city store_ids (pick 6 across cities/signals).
- _Checkpoint:_ `rca eval --dry-run` scores all scenarios; empty dir raises; `tests/test_evaluator.py` green.

**Round 1 live smoke:** one real `rca run` against a multi-city drop; eyeball the card. Commit, push, CI green.

---

# ROUND 2 — LangGraph re-platform + routing + Langfuse + memory + judge + MCP

**Outcome of the round:** the pipeline is an explicit LangGraph state graph; every LLM call is routed
(flash/pro) and traced to Langfuse; memory distills into an evolving store profile; the evaluator gains the
executive-usefulness judge; the tools are published as an MCP server.

### Phase 2.1 — LangGraph skeleton (parity first)
- Add deps: `langgraph`, `langchain-core`, `langchain-openai` (DeepSeek via OpenAI-compatible base url),
  `pydantic`.
- New `rca/graph.py`: define `RcaState` (Pydantic) and rebuild the **current** flow as a graph —
  `plan → specialists (parallel) → critic → coordinator → finance_controller → slt_brief → record → write`.
  Reuse the existing prompts/tools verbatim (they were fixed in Round 1). The stub client still powers
  dry-run; LangGraph nodes call the same client factory.
- Keep `run_coordinator` as a thin wrapper that invokes the graph, so the CLI/tests/bench don't all change
  at once.
- **Anti-theater:** the graph's conditional edges implement `plan_specialists` (skip empty domains); the
  trace records skipped nodes.
- _Checkpoint:_ dry-run via the graph reproduces Round-1 artifacts; trace shows every node; pytest green.

### Phase 2.2 — Structured output (Pydantic) replaces regex parsing
- Define Pydantic models for the **Assessment** block and the **decision card** fields; have nodes return
  structured output (function/tool-calling or `instructor`-style parsing). Delete the brittle regex in
  `outcomes.py`/`report.py`.
- _Checkpoint:_ outcome record built from typed fields; faithfulness check reads typed key_numbers; tests green.

### Phase 2.3 — Model routing (cascade)
- Config: `NODE_MODEL_MAP` (node → `fast|deep`); env overrides. Router in the client factory picks the model
  per node. Recommended map in §C (specialists/story → flash; critic/coordinator/slt/judge → pro).
- Log the chosen model per node (observable routing).
- _Checkpoint:_ unit test asserts the map; dry-run unaffected (stub ignores model); pytest green.

### Phase 2.4 — Langfuse observability
- Add `langfuse`. New `rca/obs.py`: wrap each LLM call (node name, model, tokens, latency, prompt/response)
  as a Langfuse generation under one trace per run. No PII concerns (synthetic retail data).
- **[PAUSE 3 — YOU DO]:** create a Langfuse cloud project; copy `LANGFUSE_PUBLIC_KEY` + `LANGFUSE_SECRET_KEY`
  into `.env`. Tell me when done. (If keys absent, tracing no-ops so dry-run/CI still pass.)
- _Checkpoint:_ a live run appears as one trace with per-node generations in Langfuse; dry-run green w/o keys.

### Phase 2.5 — Memory: episodic → distilled store profile
- `rca/profiles.py`: `store_profile` table (in `retail_rca`) — trigger counts, drop/lift split, common
  drivers, recurring-issue notes, last-updated, short distilled narrative.
- `rca distil [--narrative]`: rebuild profiles from `rca_outcome` (deterministic stats always; pro-model
  narrative optional). Feed the store's profile into `build_context_preamble` so each run sees its history
  (makes the card's `pattern` field evidence-backed).
- `rca replay --store <id> --signal drop [--limit N]`: run that store's trigger days in date order, calling
  `distil` between runs, and write a short "how the profile evolved" summary.
- `rca reset-memory [--store S]`: clear `rca_outcome` (+ `store_profile`) for clean replays; print what was
  cleared. Never touches dim/fact tables.
- _Checkpoint:_ write→distil→read round-trip; `reset-memory` then `replay --limit 3 --dry-run` shows trigger
  count 0→3 and `pattern` reflecting history by run 3; pytest green.

### Phase 2.6 — Bounded reflection (optional node)
- Behind `--reflect`: after the critic, if a driver is `needs_evidence`/uncalibrated AND a tool can answer
  it (e.g. stockout baseline), run exactly **one** targeted tool call + re-assessment, logged as a
  `reflect` node. Hard cap one/run.
- _Checkpoint:_ with `--reflect`, trace shows a single reflect node; without, unchanged; pytest green.

### Phase 2.7 — Evaluator: executive-usefulness judge (the business bar)
- Add an LLM judge (pro model, Langfuse-traced) scoring the card + report 1–5 on: **actionability,
  time-to-decision, format & consistency, procedure transparency, restraint** + a free-text **"Executive
  POV"** verdict ("would I act on this? what's missing?"). Keep groundedness/calibration/causal-honesty.
- Eval report shows exec scores + faithfulness gate + written verdict per scenario + aggregate.
- _Checkpoint:_ `rca eval --dry-run` includes exec scores; `tests/test_evaluator.py` green.

### Phase 2.8 — MCP server (publish read-only tools)
- Add `mcp` (FastMCP). `rca/mcp_server.py` exposes the read-only tools (`get_signal_evidence`,
  `get_*_context`, `get_stockout_baseline`, `get_prior_rca`) — thin wrappers over the same functions, each
  description carrying the data caveats (normalized sales, 5-city sample, opaque IDs). `rca mcp` launches it.
- _Checkpoint:_ `rca mcp` lists tools; a wrapper test returns the same numbers as the Python functions; tests green.

**Round 2 live smoke:** one real run → confirm Langfuse trace, routing (flash+pro both called), and the exec
judge output. Commit, push, CI green.

---

# ROUND 3 — Next.js dashboard on Vercel + skills + docs + land

**Outcome of the round:** a deployed, Supabase-reading dashboard; the story/run workflows as skills; the
README rewritten as an Agents 101; docs reconciled; scratch docs deleted.

### Phase 3.1 — Next.js dashboard (local first)
- Scaffold `dashboard/` (Next.js + TypeScript + Tailwind; charts via **Tremor** or **Recharts**; Supabase
  JS client). Read with the **anon key + RLS** (server components may use the service key for heavier reads).
- Pages/sections (mainly view — see §D for the full spec):
  - **Store performance time series** — sales line per store with **triggered dates marked** (drop/lift),
    plus same-weekday/trailing-7d baselines; descriptive stats (mean, stddev, weekday pattern).
  - **Signal grid** — store × date heatmap (port the existing one).
  - **Precomputed RCA** — list of decision cards (confidence + escalate badges) → drill into report /
    critique / story (markdown rendered from Supabase).
  - **Store profile / memory** — the evolving profile + recurrence ("stockouts in 3 of last 5 drops").
  - **Filters** — city, store, signal type, date range. **Peer view** surfaces the small-sample caveat.
- _Checkpoint:_ `pnpm dev` renders against Supabase locally; reads use the anon key under RLS.

### Phase 3.2 — Deploy to Vercel
- **[PAUSE 4 — YOU DO]:** create a Vercel project, import the repo (root = `dashboard/`); in Project →
  Settings → Environment Variables add `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`. Tell me
  when set.
- I wire `vercel.json`/build settings; you trigger the first deploy (or approve the Vercel MCP/CLI).
- **[PAUSE 5 — YOU DO]:** confirm the deployed URL loads and reads data. Verify RLS: the anon key can read
  the view tables but not write.
- Retire the old `ui/` Vite app + `rca dashboard` HTML generator (or keep as a local fallback, your call).
- _Checkpoint:_ live Vercel URL renders time series + cards from Supabase.

### Phase 3.3 — Skills
- `.claude/skills/rca-story/SKILL.md` — regenerate a reader-facing story report for a run (wraps `rca story`),
  with the grounding rules. (Optional) `rca-run` skill for an end-to-end run + card summary.
- _Checkpoint:_ skill runs on an existing run and reproduces `rca story` output.

### Phase 3.4 — Documentation (the most important deliverable)
- **README = Agents 101** (write to the §E outline): overview + funnel diagram (code vs LLM labeled);
  the one-glance component table (Agents → Tools → Model → When → What it must change); how a ReAct agent
  works (worked example); why critic/coordinator/card; how we stay honest (faithfulness, judge≠critic,
  small-sample, no currency); memory over time; model routing; **LangGraph, MCP, Skills, Langfuse, Supabase,
  Vercel** each explained; glossary; full command list; minimal data section.
- **AGENTS.md** (conflict pass): LangGraph pipeline; tool table + `get_stockout_baseline`; guardrails
  (small-sample, spend-tokens-where-hard, evaluator≠critic); **Dashboard section** (the view spec from §D);
  move MCP/Skills out of "Out of Scope"; 5-city framing.
- **CLAUDE.md**: new commands (`distil`, `replay`, `reset-memory`, `mcp`); Supabase datastore + schema;
  routing; deterministic-sanitize + one-polish; Langfuse; multi-city.
- **PRD.md**: scope/roadmap reflects shipped state (cloud, LangGraph, memory, exec judge, MCP, skills, dashboard).
- **Delete** `docs/REDESIGN_PLAN.md` + scratch md; keep README/PRD/CLAUDE/AGENTS.
- _Checkpoint:_ a fresh reader can answer "what are the agents, their tools, when each runs, where the LLM
  helps, and how to run/deploy it" from the README alone; no doc contradicts shipped behavior.

### Phase 3.5 — Land it
- Delete this plan file. Final live smoke (`rca bench` → `rca eval` → open the Vercel dashboard). Commit,
  push, `gh run list --limit 1` green.

---

## §A. Environment variables (mirrors `tcm-diagnosis` / `_newslingo_reference`)

`.env` (backend, gitignored; provide `.env.example` with blanks):
```
# Supabase (Project Settings → API)
SUPABASE_URL=
SUPABASE_SERVICE_KEY=            # service_role — backend writes only, keep secret
SUPABASE_DB_SCHEMA=retail_rca
# DeepSeek
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL_FAST=deepseek-v4-flash
DEEPSEEK_MODEL_DEEP=deepseek-v4-pro
# Langfuse (cloud.langfuse.com → Settings → API Keys) — added in Round 2
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
# LANGFUSE_HOST=https://cloud.langfuse.com   # optional
```
`dashboard/.env.local` + Vercel env (frontend; anon key only):
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```
Rules: service key **never** in the frontend or git; anon key is safe *only because* RLS restricts it to
SELECT on view tables.

## §B. Supabase schema + RLS (shape; full SQL authored in Phase 1.2)

- Schema `retail_rca`. Tables: `dim_store(store_id, city_id, …)`, `dim_holiday_day`, `dim_weather_day`,
  `fact_sales_store_day`, `fact_stockout_store_day`, `fact_discount_store_day`, `fact_activity_store_day`
  (PK `(store_id, dt)`), `signals(store_id, dt, metric, value, signal_label, …)`,
  `rca_outcome(run_name, store_id, dt, signal_label, top_driver, driver_class, confidence, escalated,
  brief_headline, decision_card_md, report_md, critique_md, story_md)`,
  `store_profile(store_id, trigger_count, drop_count, lift_count, common_drivers, recurring_notes,
  narrative, updated_at)`, `run_log_event(...)`.
- Indexes on `(store_id, dt)` and `signals(signal_label)`.
- **RLS:** `ENABLE ROW LEVEL SECURITY` on all; `CREATE POLICY anon_read ON <table> FOR SELECT TO anon USING
  (true)` on dashboard-read tables (dims, facts, signals, rca_outcome, store_profile). No anon write policy.
  Backend uses the service key (bypasses RLS). Run `get_advisors` to confirm zero RLS warnings.

## §C. Model routing (recommended map)

| Node | Model | Why |
| --- | --- | --- |
| specialists ×5, story_writer, final polish | `deepseek-v4-flash` | bounded, tool-grounded, high volume |
| critic, coordinator, finance_controller, slt_brief, evaluator/exec-judge | `deepseek-v4-pro` | synthesis + judgment |
| planner | — (deterministic code) | no LLM |

Default everything to flash; promote the table's pro rows. Each node's model is logged + traced (Langfuse).

## §D. Dashboard spec (mainly view)

Must-haves (your asks): per-store **time series** of sales with **triggered dates marked** + descriptive
stats; **precomputed RCA** decision cards with drilldown to report/critique/story.
My additions: signal grid heatmap; store **profile/memory** panel (recurrence); filters (city/store/signal/
date); confidence + escalate badges; per-store-day context overlay (stockout/discount/weather); a **peer
view that surfaces the small-sample caveat**; run/cost metadata (from Langfuse). All read-only from Supabase
(anon + RLS). No write paths in the dashboard.

## §E. README "Agents 101" outline

1. What this is + funnel diagram (label each step code vs LLM).
2. Components at a glance — one table: Agent → Tools → Model → When → What it must change.
3. How an LLM agent works — system prompt, tools, the ReAct loop (worked example), parallel specialists.
4. Why critic + coordinator + decision card — the funnel logic; calibration; confidence-led.
5. Staying honest — faithfulness check, LLM-as-judge (judge ≠ critic), small-sample caution, no currency.
6. Memory over time — episodic vs semantic, distillation, store profile, replay/reset.
7. Model routing — cheap/strong table + cost rationale.
8. The ecosystem — LangGraph, MCP, Skills, Langfuse, Supabase, Vercel (what each is + how to run).
9. Glossary (the §2 table, expanded).
10. Commands — full CLI list.
11. Data (minimal) — Supabase tables, the raw parquet, the 5-city subset.

## §F. Open defaults (flip if you disagree)

1. **5 cities = top 5 by store count** (0, 12, 3, 13, 16 ≈ 677 stores). Tell me if you want different cities
   or a smaller cut for snappier free-tier reads.
2. **Final polish OFF**, **reflection OFF**, by flag — patterns available for demo, not pervasive.
3. **Charts via Tremor** (Recharts fallback). Switch if you prefer another lib.
4. **Old `ui/` Vite app retired** once Next.js is live (kept in git history).
5. **Round boundaries are commit/deploy points** — you can stop after any round with a working system.

## §G. Pause points (all setup is yours; I continue after each)

- **PAUSE 1** (1.1): create Supabase project; provide URL + service_role key.
- **PAUSE 2** (1.2): run `0001`/`0002` migrations; confirm RLS advisor clean.
- **(soft pause, 1.3):** confirm ingest row counts before proceeding.
- **PAUSE 3** (2.4): create Langfuse project; provide keys.
- **PAUSE 4** (3.2): create Vercel project; set `NEXT_PUBLIC_SUPABASE_*` env.
- **PAUSE 5** (3.2): confirm deployed URL reads data; verify anon cannot write.
```
