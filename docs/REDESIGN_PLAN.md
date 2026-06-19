# Redesign Plan — Calibration-First RCA

> Planned on Opus. **Execute on Sonnet.** Toy project, all local, rollback-safe — no stress.
> Delete this file once merged. Each phase ends with a verification step.
>
> This plan is driven by three principles, not by "add more agents." Re-read them before
> every decision below.

## Why we are doing this (the four principles)

1. **Calibration is the product, not the prose.** The system does *correlational* RCA, not
   causal. Confidence must be first-class, structured, and propagated end to end — not buried
   in a prose "Caveats" paragraph. An executive must see *how sure we are* before *what we think*.
2. **Every node must change the output.** No agent theater. If a node only rewords what an
   earlier node said, cut it. The critic must downgrade/flag real claims; the planner must
   skip empty domains; the exec layer must elevate, not summarize.
3. **Evidence-first; the metric layer is a future moat, not this prototype.** Every claim
   traces to a tool number. We do NOT fabricate data (esp. margin) to look richer. Where data
   is missing, we say so — that honesty *is* calibration.
4. **Every stage is inspectable.** We build the full pipeline in one pass (no pausing), but it
   must be troubleshootable: when the final card is wrong, you can walk back and see exactly which
   node caused it. Each node records what it received and produced; failures surface loudly with
   the node name; nothing is swallowed. Debuggability is a design requirement, not an afterthought.

## Decisions (locked by the user)

- Build the **executive brief layer** (finance controller + SLT) — the headline deliverable.
- Build a **lightweight critic** (one bounded pass, no infinite loop).
- Upgrade **commercial analyst** toward margin — but honestly (see "Margin" below; we do not
  have cost/margin data, so we surface the *risk and the data gap*, we do not invent numbers).
- Web search for the research analyst: **snippets only, no page-fetch.** `search_news` returns
  title + URL + a 1-2 sentence snippet per result; it does NOT open the page. That is enough for
  a shallow "was there a notable event near this date" signal. Do NOT build a `fetch_page(url)`
  tool yet — it adds cost/fragility for marginal value. The research analyst reasons over snippets
  with the existing DeepSeek model and must stay LOW-confidence and gated off by default, because
  searching *today* for a 2024 date is retrospective and approximate, not point-in-time.
- Rollback is fine. Toy. Local only.

## Target architecture

```
[ context_pack ]          # built ONCE, stored, injected into every prompt (grounding)
[ get_prior_rca tool ]    # reads past outcomes → "is this a pattern?" becomes evidence-backed

Input (store, dt)
  → plan_specialists        # selective: skip domains with no signal (anti-theater)
  → [analysts in parallel]  # each ends with a STRUCTURED ASSESSMENT block (calibration)
  → critic                  # one pass: downgrade unsupported claims, flag correlation-as-cause
  → coordinator             # filter + synthesize → analyst-grade RCA, drivers RANKED by confidence
  → finance_controller      # financial read: materiality, margin risk, one-off vs structural
  → slt_brief               # final DECISION CARD: confidence-led, one action, escalate y/n
  → record outcome          # write structured result to outcomes store (feeds get_prior_rca)
  → artifacts               # decision card is the PRIMARY artifact; RCA becomes the drill-down

Offline (not in the run):
  evaluator                 # LLM-as-judge + deterministic faithfulness check, over the benchmark
```

Node-by-node, and what each one is REQUIRED to change (principle 2):

| Node | Type | Must change the output by… |
| --- | --- | --- |
| `plan_specialists` | logic (no LLM) | Dropping analysts whose domain shows nothing; always keep `sales_analyst` |
| 5 analysts | agent (parallel) | Producing a structured Assessment (verdict + confidence + evidence) per domain |
| `critic` | agent | Downgrading/flagging at least the weakest claim; listing gaps; policing causation |
| `coordinator` | agent | Ranking drivers by confidence and folding in the critic's adjustments |
| `finance_controller` | agent | Adding the $ materiality + margin-risk framing the analysts lack |
| `slt_brief` | agent | Compressing to a confidence-led decision; explicitly allowed to say "noise, monitor" |

## Calibration primitives (the spine — implement first, in config + prompts)

### Confidence vocabulary (define once, use everywhere)

Add to `rca/config.py` as a constant string the prompts import, so every node uses identical definitions:

- **HIGH** — multiple independent evidence points align; the number clears its threshold with
  margin; alternative explanations are weak.
- **MEDIUM** — evidence points one way but is single-source or has a plausible alternative.
- **LOW** — suggestive only; correlational; or partly contradicted by another signal.

### Driver classification (the coordinator labels each candidate driver)

`cause` | `contributing` | `ruled_out` | `inconclusive`

### Structured Assessment block (every analyst ends its memo with this)

Keep it as a fixed markdown section — human-readable in artifacts, parseable enough for a toy.
JSON/tool-call structured output is a future hardening, noted but not required now.

```
## Assessment
- verdict: <is your domain a driver? cause | contributing | ruled_out | inconclusive>
- confidence: <high | medium | low>
- key_numbers: <the 1-3 numbers that matter, with values>
- causal_caveat: <correlation-vs-causation note, or "n/a">
- data_gaps: <what you could not see, or "none">
```

The coordinator, critic, and exec layers all read these blocks. This is how confidence propagates.

## New / changed nodes — detail

### plan_specialists (anti-theater, selective dispatch)
- Currently returns all 5. Change it to read cheap **local** evidence first (the `get_*_context`
  tools are local DuckDB — fast, free, no LLM) and dispatch only analysts whose domain shows a
  non-null signal.
- Rules: always run `sales_analyst` (the anchor). Run `ops_analyst` only if any stockout signal
  is present; `commercial_analyst` only if discount or activity is present; `market_analyst`
  always (cheap context, and needed to test store-specific vs fleet-wide); `research_analyst`
  optional/off by default (it makes external calls — gate behind a flag).
- Be conservative: when a domain is ambiguous, run it. Log which analysts were skipped and why
  (so the trace shows the planner actually did something — measurable anti-theater).

### Analyst Assessment block
- Append the Assessment format to all five system prompts. Tighten each prompt so the analyst
  may return "inconclusive / nothing material" cheaply instead of padding (principle 2).
- `commercial_analyst`: add margin handling — see below.

### critic (new node, `rca/agents.py`)
- Runs AFTER analysts, BEFORE the coordinator (single synthesis pass that already incorporates
  the critique — cheaper than a reflection loop, still changes output).
- Persona: a skeptical senior reviewer. Input: all analyst memos + Assessments.
- Job, per claimed driver: (a) is it supported by the cited numbers? (b) is the confidence
  calibrated or over-claimed? (c) is correlation being sold as causation? (d) what is missing?
- Output: a structured **review note** — per-claim verdicts (`keep` / `downgrade` /
  `flag_correlational` / `needs_evidence`) plus a short gap list.
- The coordinator is REQUIRED to fold this note in (downgrade confidences, add a
  "What we might be wrong about" line). If the critic changes nothing, that is a red flag worth
  seeing in the trace.
- Bounded: exactly one critic pass. No loop. (Reflection loop = optional future v2, note only.)

### coordinator (changed)
- Consumes memos + Assessments + critic note.
- Output RCA must: rank drivers by confidence; label each with the driver classification; carry
  an explicit confidence per driver; keep a short "What we might be wrong about" section sourced
  from the critic. Keep the existing 5 sections but lead Likely Drivers with confidence.

### finance_controller (new node)
- Input: coordinator RCA only (not raw evidence — different altitude).
- Persona: skeptical CFO-office controller. Output is 3-4 pointed lines, not a rewrite:
  - **Materiality**: size the impact in money and as a % of something meaningful; is this worth
    attention vs noise?
  - **Margin risk**: if a promo is involved, flag that volume ≠ value and that a discount-driven
    move may be margin-dilutive. (We have no margin data — say so and demand it; do not invent.)
  - **One-off vs structural**: e.g., a multi-day decline reads structural, which changes exposure.

### slt_brief (new node — the PRIMARY deliverable, a DECISION CARD)
- Input: coordinator RCA + finance_controller note + prior-RCA pattern info.
- Persona: a director reading 20 of these a day, zero patience.
- Output is a fixed **decision card** — one screen, ~10 seconds to read. Fixed fields stop the
  model rambling and force compression:

  ```
  ## Decision Card — <store> <date>
  - headline: <one line: what happened, confidence-led, e.g. "High confidence: mid-day
    stockouts drove a 25% drop">
  - confidence: <high | medium | low>
  - materiality: <is this worth attention? size it; or "immaterial / noise">
  - pattern: <recurring or first-time, from prior-RCA history>
  - action: <the ONE recommended next step, or "none — monitor">
  - escalate: <yes / no>
  ```

- CRITICAL instruction: it is explicitly allowed — encouraged — to set action "none — monitor"
  and escalate "no". A tool that cries wolf on every variance gets ignored. Restraint is the
  credibility. Most single store-day blips are noise and the card should say so.

## Margin handling (honest, per principle 3)

The DuckDB schema has discount rates and activity rates but **no cost or margin data**. So:
- `commercial_analyst` does NOT compute margin. It raises the margin *question* as a flagged risk
  ("38% of sales promoted; a promo-driven lift may be margin-dilutive — margin data unavailable")
  and records it under `data_gaps`.
- `finance_controller` amplifies this into a materiality/value caution.
- This is a feature, not a limitation: it demonstrates calibrated honesty about what we cannot see.

## Context pack (compute once, store, inject — grounding)

A small, FACTUAL grounding artifact built once and reused every run. It raises calibration: an
agent that knows what "normal" looks like is much better at judging whether a move is unusual.

**Conservative rule (per the user — this is strict):** the raw data is old, anonymized, and
context-poor — it is mostly opaque IDs. So the pack includes ONLY things computed directly from
the data. **When unsure whether something is real or meaningful, OMIT it.** Do not interpret
anonymized identifiers. A label whose meaning is not documented is either left out or stated as
an opaque grouping / a computed observation — never given an assumed business meaning.

> Concrete bug this prevents: the current h555 report calls the store "top tier (H)" and reasons
> from it. Nobody confirmed that the `h` prefix means "high tier" — that is an assumption about an
> anonymized ID. The pack must NOT assert it. At most it may state a *computed* fact ("h-prefix
> stores have higher average daily sales in this data, $X vs $Y") if that is actually true in the
> numbers; otherwise the prefix is just an opaque grouping key for peer comparison.

- Built by a command (new `rca profile`, or folded into `rca analyze`). Stored as
  `data/context_pack.json` (+ a readable `.md`). Rebuilt only when the data changes — never per run.
- Contents (all computed from the DB; omit anything uncertain):
  - dataset scope: 15 stores, 90 days (2024-03-28 to 2024-06-25), store-day granularity, what
    each fact table measures (factual);
  - per-store normal: typical daily sales and volatility (computed);
  - fleet baselines: average sales, weekday/weekend pattern, the in-window holiday calendar
    (computed; note `holiday_name_inferred` is itself *inferred* — flag it as uncertain);
  - the store-alias prefix (h/m/l) as an opaque grouping key, with the empirical sales difference
    if and only if it exists in the data — NOT labelled "tier" unless documented;
  - provenance + limitations: FreshRetailNet-50K, an anonymized 2024 dataset; `city_id`, store
    aliases, and product IDs are opaque; treat all context as a weak prior, not ground truth.
- Injected as a short grounding preamble into analyst + coordinator prompts. Keep it SMALL — a
  giant dump bloats every prompt; distill to essentials.
- **Timing guardrail:** the pack states "today = the store-date." Agents must not reference events
  after the data window or invent current-day facts. There is no real company — context = what is
  normal in the data + provenance, never a fabricated backstory.

## Memory — collect and distil over time

One-shot RCA has no memory, so the "is this a pattern?" question is currently guessed. Fix it:

- **Outcomes store:** after each run, write the structured result to a `rca_outcome` table in
  `data/runs.duckdb`: store, dt, signal, top_driver, driver_class, confidence, escalated, brief.
- **`get_prior_rca(store)` tool:** reads that table so the coordinator / slt_brief can ground the
  pattern question in evidence ("this store dropped on stockouts 4 of the last 8 triggers")
  instead of speculating. This is principle 1 (calibration) applied to recurrence.
- **Distillation (optional, later):** a periodic step (`rca distil`) rolls outcomes into a
  per-store narrative that feeds back into the context pack. Can be a simple aggregation first;
  an agent-written summary later. This is the "collect and distil over time" loop closing.

## Evaluation — a separate judge agent (NOT the critic)

Honest reality: RCA has no ground-truth "correct cause," so you cannot compute accuracy. Real
evaluation scores *quality dimensions*. Keep this strictly separate from the critic:

- **critic** = inside the run, improves THIS output before it ships.
- **evaluator** = offline, scores runs to tell whether the SYSTEM is improving. Does not change
  the run it scores. Runs over the whole benchmark set.

Build:
- **`evaluator` agent (LLM-as-judge):** scores each RCA on a rubric — groundedness (every claim
  cites a real number), calibration (stated confidence matches evidence strength), actionability
  (is the decision card decision-useful), conciseness, causal honesty (no correlation-as-cause).
  Outputs scores + short rationale per dimension.
- **Deterministic faithfulness check (non-LLM, cheap):** verify the numbers an analyst cites
  actually appear in the tool outputs for that run. Catches hallucinated figures for free.
- **Reference check (we have partial labels):** the benchmark scenarios carry `expected_signal`
  (drop/lift); confirm the system recovered the right signal and named a plausible driver.
- Wire as `rca eval` over the benchmark → writes an eval report (scores per scenario + aggregate).
  This is the regression signal: did a prompt change help or hurt?
- **Honest caveat (document it):** the judge is also an LLM and fallible. Sanity-check it against
  occasional human spot-checks; never treat judge scores as truth.

## File-by-file changes

- `rca/config.py` — add `CONFIDENCE_VOCAB` constant; add `ASSESSMENT_FORMAT` constant;
  add `CONTEXT_PACK_PATH` (`data/context_pack.json`).
- `rca/context.py` (new) — `build_context_pack()` computes the factual grounding pack from the DB
  and writes `data/context_pack.json` + `.md`; `load_context_pack()` returns a short prompt preamble.
- `rca/agents.py` —
  - rewrite analyst system prompts to require the Assessment block + allow "inconclusive",
    and to prepend the context pack preamble;
  - make `plan_specialists` selective (reads local evidence, logs skips);
  - add `_run_critic(...)` and a `CRITIC_SYSTEM_PROMPT`;
  - add `_run_finance_controller(...)` and `_run_slt_brief(...)` (decision card) with their prompts;
  - extend `CoordinatorResult` with `critic_note`, `controller_note`, `decision_card_markdown`;
  - wire the new nodes into `run_coordinator` (analysts → critic → synthesize → controller → slt);
  - record the run outcome to the `rca_outcome` table after the card is produced;
  - log every new node to the run log (actor_name = node name) so the trace shows contribution.
- `rca/tools.py` — add `get_prior_rca(store_alias)` reading the `rca_outcome` table; register it
  and grant it to the coordinator (and optionally slt_brief).
- `rca/outcomes.py` (new) — schema + write/read helpers for the `rca_outcome` table in
  `data/runs.duckdb`.
- `rca/evaluator.py` (new) — the judge agent + deterministic faithfulness check + reference check;
  `evaluate_run(...)` and `evaluate_benchmark(...)`.
- `rca/report.py` — render the decision card as its own artifact (`decision_card.html`),
  styled as the headline; the full RCA renders as the drill-down.
- `rca/stubclient.py` (new) — a deterministic stub LLM client + client factory that returns
  canned, well-formed responses per node (analyst memo with Assessment block, critic note,
  coordinator RCA, controller note, decision card). No network, no API key. This is what powers
  `--dry-run` and is reused by tests. It is the backbone of the defensive checkpoints below.
- `rca/cli.py` — `rca run` prints the decision card (not the full RCA) by default; add `--full`
  to print the RCA too; add `--dry-run` (wires the stub client factory — exercises the whole chain
  with no API). `--quick` still = sales_analyst only, no exec layer. Add `rca profile`
  (build context pack), `rca eval` (run evaluator over benchmark), optional `rca distil`.
- `rca/bench.py` — benchmark output adds the decision card per scenario; manifest links it.
- `tests/test_agents.py` — add fakes for critic / controller / slt nodes; assert the decision card
  exists, confidence labels propagate, and a skipped-analyst path works.
- `tests/test_evaluator.py` (new) — test the deterministic faithfulness check with fixtures.

## Output / artifacts

- `decision_card.md` + `.html` — the PRIMARY artifact (what a director opens).
- `report.md` / `report.html` — the analyst RCA drill-down (unchanged location).
- `critique.md` — the critic's review note (new; makes the QC visible).
- specialists/*.md — unchanged, but now each ends with an Assessment block.
- `data/context_pack.json` + `.md` — grounding pack (built once).
- `rca_outcome` table in `data/runs.duckdb` — structured run history (feeds `get_prior_rca`).

## Phased execution — defensive, gated checkpoints

Build all 12 phases in one pass (no pausing for review), but **each phase is a hard gate.** Do not
start a phase until the previous phase's checkpoint is GREEN. The phasing exists so a failure is
caught the moment it is introduced, not three phases downstream where it is expensive to find.

### Checkpoint discipline (applies to every phase)

A checkpoint is GREEN only when ALL of these pass. If any is RED: fix it, or `git restore` the
phase and rethink. **Never proceed on red.** Commit each phase only after its checkpoint is green
(small commits = clean rollback points).

1. **Import check** — `uv run python -c "import rca"` succeeds.
2. **Targeted tests** — the unit tests for the phase pass, and `uv run pytest` stays fully green
   (no regression in earlier phases).
3. **Dry-run smoke test** (for any phase that touches the run pipeline) — `uv run python -m
   rca.cli run --store h555 --dt 2024-05-16 --dry-run` completes, using the stub client (no API),
   and produces the expected artifacts/fields. This proves the *plumbing* deterministically and
   for free: planner → analysts → critic → coordinator → exec → outcome → artifacts + trace.
4. **Trace sanity** — open `run_trace.json` from the dry run and confirm every node recorded an
   input and an output, and the new node actually appears.

Two kinds of smoke test, kept distinct:
- **Dry-run (stub client):** deterministic, free, no network. The mandatory per-phase gate.
- **Live smoke (real DeepSeek):** ONE real `rca run` against one scenario. Costs a few API calls
  and is non-deterministic, so it is NOT a per-phase gate — run it once at Phase 9 to confirm real
  integration, and any time a dry-run passes but you suspect a prompt-quality problem.

### Phases

1. **Branch** `redesign/calibration-first` off main.
   _Checkpoint:_ `uv run pytest` green on a clean branch (baseline).
2. **Stub client first** (de-risks every later phase): add `rca/stubclient.py` + wire `--dry-run`
   into `rca run` against the CURRENT pipeline.
   _Checkpoint:_ `rca run ... --dry-run` produces today's report with no API call; pytest green.
3. **Calibration spine:** add `CONFIDENCE_VOCAB` + `ASSESSMENT_FORMAT`; append the Assessment block
   to analyst prompts; update stub analyst responses to include it.
   _Checkpoint:_ dry-run shows the Assessment block in each specialist memo; pytest green.
4. **Context pack:** add `rca/context.py` + `rca profile`; inject the preamble.
   _Checkpoint:_ `rca profile` writes `data/context_pack.json`; **manually read the `.md` and
   confirm it asserts nothing about anonymized IDs** (no "tier" labels — the conservative rule);
   dry-run still green.
5. **Critic node:** add `_run_critic` + prompt; wire before the coordinator; coordinator consumes it.
   _Checkpoint:_ unit test with fakes; dry-run shows a `critique.md` and the trace shows the critic
   node with input+output; pytest green.
6. **Executive layer:** add `finance_controller` + `slt_brief` (decision card); extend
   `CoordinatorResult`; wire in.
   _Checkpoint:_ dry-run produces `decision_card.md` with all fixed fields populated and a
   confidence-led headline; unit test asserts the card; pytest green.
7. **Selective planner:** make `plan_specialists` skip empty domains, log skips, gate research.
   _Checkpoint:_ unit test that a no-stockout fixture skips `ops_analyst`; dry-run trace shows the
   skip logged with a reason; pytest green.
8. **Memory:** add `rca/outcomes.py` (`rca_outcome` table) + `get_prior_rca`; record after each run.
   _Checkpoint:_ write→read round-trip test; a second dry-run for the same store shows the `pattern`
   field reflecting the first run; pytest green.
9. **Evaluation + LIVE smoke:** add `rca/evaluator.py` + `rca eval` (deterministic faithfulness
   check + judge rubric + reference check).
   _Checkpoint:_ `tests/test_evaluator.py` (the deterministic check on fixtures) passes; THEN run the
   one live smoke — a real `rca run` against `h555 2024-05-16` — and eyeball the decision card for
   sanity; pytest green.
10. **Artifacts + CLI + bench polish:** card/critique rendering, `rca run` prints card by default
    (`--full` for RCA), bench links the card.
    _Checkpoint:_ `rca dashboard` still works; `rca run --help` shows `--dry-run`/`--full`; dry-run
    green; pytest green.
11. **Docs:** update `README.md`, `AGENTS.md`, `CLAUDE.md` (see below); update the DAG diagram.
    _Checkpoint:_ docs match the shipped behavior (no stale references); pytest green.
12. **Land it:** delete this plan file, commit, push, `gh run list --limit 1` → green.

## Docs to update at the end (Phase 11)

- **README.md** (agentic workflow + data management focus, per the user): replace the specialist
  table with the full pipeline; add a short "Calibration" subsection (confidence levels, output is
  correlational not causal); describe the decision card as the primary output; document the context
  pack, the over-time memory (`get_prior_rca`), and `rca eval`; update the DAG. Do NOT add
  data-internal sections.
- **AGENTS.md** (conflict pass — re-read first): record the three principles as standing guardrails;
  add critic + executive nodes + evaluator to the architecture and tool/role table; note "every node
  must change the output", "calibration is first-class", and "evaluator is separate from critic" as
  guardrails; keep out-of-scope list current.
- **CLAUDE.md**: note `rca run` prints the decision card by default (`--full` for the RCA); note new
  commands (`rca profile`, `rca eval`, optional `rca distil`) and artifacts (decision_card, critique,
  context_pack, the `rca_outcome` table).

## Observability — troubleshooting + anti-theater (principles 4 and 2)

The pipeline is a chain; when the final card is wrong, you must be able to find the broken link.
Same mechanism also proves each node earns its place. Requirements:

- **Full per-node trace.** Extend `manager_trace.json` (rename → `run_trace.json`) so it records,
  for every node, its **input** (what it received) and **output** (what it produced) — not just
  events. Walking this top-to-bottom should answer "where did it go wrong": bad analyst evidence?
  critic missed it? coordinator misranked? exec over-elevated?
- **Each node logs what it decided/changed** in the run log `details`: planner → which analysts it
  skipped and why; analysts → verdict + confidence; critic → counts of downgraded/flagged claims;
  coordinator → driver ranking; finance_controller → materiality call; slt_brief → escalate y/n.
- **Failures surface loudly, never swallowed.** If a node errors (LLM error, bad tool args, missing
  evidence), raise with the node name and its input in the message. A partial run must say which
  node failed, not silently produce a degraded card. (The existing `search_news` try/except that
  returns `{"error": ...}` is the right shape — apply that discipline, but make the error visible
  in the trace, not hidden.)
- **A run is replayable from its trace.** Because every node's input/output is captured, a human or
  the evaluator can inspect any single stage without re-running the whole pipeline.
- **Anti-theater check:** if a node's log shows it never changes anything across runs (critic never
  downgrades, planner never skips), it has failed principle 2 — flag it for cutting.

## Rollback

Everything is on a branch. If the redesign feels worse than the current flat coordinator, the
old behavior is one `git checkout main` away. Nothing here touches data or the DB schema.
