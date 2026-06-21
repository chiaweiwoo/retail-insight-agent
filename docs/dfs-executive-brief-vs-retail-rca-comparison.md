# DFS Executive Summary vs Retail RCA — Design Comparison

A side-by-side analysis of two generations of multi-agent RCA systems, written to support interview preparation. The DFS project was a first-generation internal system; the Retail RCA project is a redesign that addresses its structural weaknesses.

---

## Side-by-Side Architecture Comparison

### The Graph Shape

| Dimension | DFS Executive Summary | Retail RCA |
|---|---|---|
| Graph topology | Fixed: deviation → check → [5 agents in parallel] → manager → critique loop → report | Dynamic: investigation_loop (planner selects agents per round) → coordinator → evaluation → memory → record |
| Agent selection | All 5 agents always fire if deviation is out of range — no selection logic | Planner reads the signal and picks which agents to run this round |
| Investigation loop purpose | Polish the text (manager rewrites based on critique style feedback) | Gather more data (critic identifies missing evidence types, triggers more tool calls) |
| Loop termination | String `"SATISFACTORY"` found in critique output, or 5 max iterations | Critic's `confidence_ceiling == "high"` and gaps are minor/unavailable, or max rounds |
| Model routing | Everything uses `gpt-4.1-mini` | Fast model for tools/planner/critic, deep model for coordinator/reviewer |
| Memory | None — every run starts blank | Lessons written to `rca.memory`, loaded by planner on subsequent runs |
| Evaluation | Token cost tracking only (observability) | 8 deterministic audit checks + LLM alignment judge with 0–1 score |
| Evidence traceability | Free-text strings (`sales_tool_summary: str`) | Typed `EvidenceItem` ledger — every observation and inference has an ID and source |

---

## The Five Specific Problems

### 1. The LLM is used to compute a number

In DFS, `sales_deviation_agent` wraps a single Python function (`sales_deviation_calculator`) inside a `create_tool_calling_agent` + `AgentExecutor`. The LLM is asked to call one tool and return a float. This is an anti-pattern: you are paying LLM cost and adding non-determinism to a computation that is just `(actual - forecast) / forecast * 100`. If the LLM misformats the output, `result.get("output")` silently returns the wrong number.

**Retail RCA fix:** the signal is computed once offline by `rca signal` (deterministic pandas), written to `rca.signals`, and never re-derived at runtime.

---

### 2. No planner — all agents always run

DFS's `route_deviation` function does one thing: if deviation is within -10% to +15%, skip everything; otherwise run all 5 agents. There is no mechanism to say "this looks like a promotions story, don't waste tokens on news" or "inventory is already well-stocked, skip it." Every run has the same cost regardless of what the signal actually implies.

**Retail RCA fix:** the planner is a dedicated LLM call that reads the signal, calendar context, and prior memory, then returns a JSON list of agents selected for this round plus a rationale. The cost of a straightforward holiday lift (run statistician + calendar agent, confidence high, stop after round 1) is lower than a complex supply-shock drop (run all agents, critic finds gaps, run round 2 with inventory + news agent).

---

### 3. The critique loop never gains new information

In DFS, the manager → critique loop runs up to 5 times. On each iteration, the manager receives the same five tool summaries and rewrites the prose based on style feedback. No new Snowflake queries are made. The critique checks: does the report have baseline values? Is driver order correct? Is the language executive-level? These are valid quality checks, but they are **formatting and consistency checks**, not evidence-gap checks. At iteration 5, you have spent 5× the LLM cost and have a better-worded version of the same analysis.

**Retail RCA fix:** the critic identifies **typed gaps** (`missing_internal_evidence`, `missing_external_context`, `baseline_conflict`, `unavailable_data`) and its `continue_investigation` decision triggers the next round with new tool calls. The loop grows the evidence base, not just the prose.

---

### 4. No evaluation means no measurable quality

DFS has an `observability.py` that tracks token counts and latency per agent — useful for cost management. There is no mechanism to score the output's quality. You cannot answer: "Is today's report better than yesterday's? Is location A's analysis more reliable than location B's? If I change the manager prompt, did it improve?"

**Retail RCA fix:** every run produces an `eval_score` (0–1, 8 deterministic checks) and an `alignment_score` (0–1, LLM judge). The `rca.simulate_review` table stores these per run. You can run a batch across all signal dates and compare average alignment scores before and after a prompt change.

---

### 5. Prompts are doing five jobs at once

The DFS manager prompt is ~400 lines. It encodes: output format rules, baseline compliance requirements, contradiction avoidance logic, iteration tracking (which iteration am I on?), zero-sales protocol, driver prioritization rules, JSON formatting rules, and domain knowledge. The critique prompt is ~500 lines doing the same. When something goes wrong in the output, it is extremely hard to identify which section of the prompt failed. The system is also fragile to model version changes — any update that handles the prompt differently can break the output format.

**Retail RCA fix:** each node has a narrow mandate. The planner prompt is ~10 lines ("select agents, return JSON"). The critic prompt is ~20 lines ("return JSON with gaps and a stop decision"). The coordinator prompt is ~30 lines. Evaluation logic is in Python, not in the prompt. The prompts are testable in isolation.

---

## What "No Subagent" Actually Means

The critique — "didn't use subagents" — refers to this: in DFS, every specialist (traffic, sales, inventory, etc.) is a **fixed node** that always runs. There is no orchestrating agent that decides at runtime which sub-processes to invoke.

In production-grade multi-agent design, a subagent is:
1. Spawned dynamically by a parent (planner/coordinator)
2. Given a specific objective derived from the current investigation state
3. Returns results that change what the parent does next

DFS's specialists are not subagents — they are fixed pipeline stages. The "manager" receives all five outputs regardless of what they contain. There is no dynamic coordination.

Retail RCA's planner + specialist pattern is the minimal correct form of this: the planner decides which agents to spawn per round, based on the signal and what the critic said was missing last round. The critic's `suggested_agents` field tells the planner who to dispatch next. This is the **planner-executor pattern**.

---

## Interview Framing

### The Narrative Arc

> "In the first version (DFS), we were at the 'make it work' stage. We got multi-agent orchestration running end-to-end with LangGraph, connected it to our internal data sources, and put a Streamlit UI on top. But in production we noticed several problems: the loop was polishing prose rather than gathering more evidence, there was no systematic quality scoring so we couldn't tell if one run was better than another, and every deviation triggered all five agents regardless of the signal type — so cost was unpredictable.
>
> In the redesign (Retail RCA), I addressed each of these directly: I separated precomputed signal detection from the agent run, added a planner node that dynamically selects agents based on the signal, changed the critic's job from style-reviewer to evidence-gap-detector, added a typed evidence ledger for traceability, and built a two-layer evaluation system — eight deterministic rule checks plus an LLM alignment judge — so I can score every run and compare across batches. I also added cross-run memory so the planner learns from prior investigations of the same location."

---

### Specific Talking Points (Show Engineering Maturity)

**On deterministic vs LLM computation:**
> "We used an LLM to compute a float in the first version. I moved that to a deterministic precompute step because LLMs introduce cost and variance into what should be a formula."

**On the loop design:**
> "The critique loop in v1 ran up to five iterations over the same data. That's prompt engineering masquerading as intelligence. I redesigned the loop so each iteration actually calls new tools and gathers evidence the previous round didn't have."

**On evaluation:**
> "I introduced deterministic evaluation before LLM evaluation. Hard rules catch outright violations cheaply. The LLM judge then adds nuanced scoring on top. You need both — the deterministic layer is cheap and reliable, the LLM layer catches subtler failures like overconfident calibration."

**On model routing:**
> "Model routing was a cost and quality win. The planner and critic don't need deep reasoning — they need consistent JSON. The coordinator synthesises across all the evidence and needs better reasoning. Running everything on the same model was leaving quality on the table in one place and wasting cost in the other."

---

### The Question They Will Ask

**"What would you do differently if you had to build this again from scratch?"**

> "I'd invest earlier in the evaluation layer. In both versions, the most time was spent on the agent logic — what agents exist, what tools they call, what prompts they get. But the thing that tells you whether any of that is working is evaluation. Without a score you can track per run, you're flying blind every time you change a prompt. I'd build the scoring harness first, then build the agents — so every prompt change can be A/B tested against a consistent baseline."

---

## One-Paragraph Summary

The DFS project demonstrated that you can wire LangGraph together and get a multi-agent pipeline to run end-to-end. The Retail RCA project demonstrates that you understand **why** a naive pipeline fails at scale: fixed agent selection is expensive and non-adaptive; critique loops that don't gather new data are expensive polish; unscored output means you can't measure progress; untraced evidence means you can't audit claims. The redesign addresses each failure mode with a specific engineering decision. That is the story that separates "I used LangGraph" from "I understand production AI system design."
