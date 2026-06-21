# ADR 0002: Agentic Investigation Upgrade

## Status

Accepted for next implementation phase.

## Context

The v2 system currently has a useful LangGraph workflow:

1. plan
2. run selected specialists
3. critique
4. coordinate
5. distill memory
6. record

This is a good learning scaffold, but it is still closer to a planner-driven workflow than a fully adaptive agent. The next learning goal is to make the system behave more like an autonomous analyst: it should form hypotheses, collect evidence, update its plan, decide when it knows enough, and produce management-ready decision output.

## Decisions

- Keep the project hybrid: deterministic workflow for guardrails, agentic loops for investigation.
- Add an investigation controller that manages hypotheses, evidence, open questions, confidence, next actions, and stop conditions.
- Upgrade the final output from analyst notes into a management decision brief.
- Add a claim-evidence ledger so important claims are tied to observed evidence and confidence.
- Make memory operational: retrieved memory should visibly affect planning, interpretation, or caveats in later runs.
- Keep the news/web agent, but enable broader external research only after the internal RCA loop is stable.
- Add ML/stat analysis tools only when the agent can explain why it needs them and what decision the analysis supports.
- Strengthen calibration rules: the agent must be allowed, and expected, to say "unknown", "not enough evidence", or "requires follow-up data" instead of forcing a cause.
- Improve the signal layer as an entry-point and prioritization layer, not as a replacement for runtime reasoning.
- Add an evaluation harness that checks output quality, grounding, calibration, actionability, scope discipline, and regression stability.

## Rationale

Pure workflow systems are easier to test but can become rigid. Pure agent systems can adapt, but they are harder to debug and can become expensive or ungrounded. This project should teach the middle path used by many practical AI systems:

- deterministic rails for ingestion, permissions, persistence, and auditability
- agentic reasoning for investigation, planning, and decision synthesis
- evaluation layers to keep the agent honest as it evolves

## Signal Layer Direction

`rca signal` remains a screening layer. It should answer:

- is this city/date worth investigating?
- how severe is the signal?
- how trustworthy is the baseline?
- what first hypotheses should the agent consider?

The signal layer should stay transparent and business-readable. It can become richer with fields such as `signal_strength`, `baseline_quality`, `signal_reason`, `confidence`, and `priority_score`, but it should not hide the RCA inside precomputed statistics.

## Decision Brief Direction

The final RCA output should become decision-grade:

- situation
- business impact
- most likely explanation
- supporting evidence
- recommended action
- alternatives
- owner or accountable function
- urgency
- expected benefit
- confidence
- what to monitor next
- caveats and unknowns

The agent must not invent currency, margin, product, or store-level facts when the runtime evidence does not contain them.

## Evaluation Direction

The refactor should be protected by a moderate but real test harness:

- unit tests for deterministic transforms and signal fields
- integration tests for `build`, `signal`, and `run` smoke paths
- golden-case fixtures for known city/date examples
- prompt/output audits for required sections and forbidden claims
- LLM-as-judge checks for higher-level quality, with deterministic rule checks taking priority
- regression tracking for whether memory changes future planning in a visible way

The evaluator should remain separate from the critic. The critic improves a single run; the evaluator judges whether the system design is improving over time.
