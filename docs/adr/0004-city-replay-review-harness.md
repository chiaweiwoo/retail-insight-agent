# ADR 0004: City Replay and Self-Review Harness

## Status

Implemented (commit following Phase 3 / ADR 0003).

## Context

After Phases 1–3 delivered the bounded investigation loop, deterministic audits, and gated stat tools, a review of the system revealed two gaps:

1. **No end-to-end verification**: CI only ran `import ok`. The dry-run path (`--dry-run` / stub client) was silently broken — `str.format()` in the stub client collided with literal JSON braces introduced in Phase 2's structured outputs, causing a `KeyError` on every dry-run. This went undetected because there was no integration test.

2. **No way to systematically assess output quality**: Running `rca run` on one date gives one result. There was no mechanism to replay all triggered dates for a city, accumulate memory across them (the actual learning-mode use case), and compare quality before/after changes.

This ADR records the decisions made to address both gaps.

## Decision 1 — Fix the stub client and add an integration test

`str.format()` was replaced with `str.replace("{city}", ...).replace("{dt}", ...)` in `rca/stubclient.py`. This affects only the two actual placeholders in the `news_query` stub and is safe for all other stubs (which contain no `{...}` sequences).

A new `tests/test_graph_integration.py` runs the full LangGraph graph (`investigation_loop → decision → evaluation → memory → record`) end-to-end through the stub client, with Supabase calls patched at the module-import boundary. This test would have caught the stub crash immediately. It is now part of CI via the `import ok` check (which imports the graph) and `pytest` (which runs the test). Future sessions must not break this test.

## Decision 2 — Reset scope: everything including caches and memory

`rca replay --city N` deletes: `outcomes`, `events`, `completions`, `memory`, `evidence_cache`, `external_events` for the city. Signals and base tables (`sales`, `inventory`, etc.) are never touched.

Rationale: a full cold-start reset makes each batch reproducible and comparable. If you want to accumulate on top of existing memory (e.g., to test whether a prompt change improves on an already-warmed city), use `--no-reset`. Deleting `evidence_cache` forces fresh tool calls, which is correct when you want to measure whether the investigation itself improved, not just whether the cache helped.

## Decision 3 — Alignment reviewer on by default

The LLM alignment judge runs after every date in a replay batch, using the deep model. Rationale: the replay harness is explicitly for quality improvement iteration, not production throughput. The cost of one extra LLM call per date is acceptable. Under `--dry-run`, the stub client handles `"reviewer"` without a real API call. Under `--no-review`, the LLM judge is skipped entirely.

The reviewer prompt (`REVIEWER_ALIGNMENT_PROMPT` in `rca/reviewer.py`) covers eight criteria grouped into hard guardrails (city/date grain, no currency, internal evidence primary, confidence calibrated, "unknown" allowed) and usefulness criteria (actionable recommendation, concrete monitoring, evidence traceability, honest caveats).

## Decision 4 — `rca.replay_review` table for incremental improvement

One row per (batch, city, date). Columns: `batch_id`, `run_id`, `eval_score`, `eval_passed`, `alignment_score`, `alignment_label`, `pros`, `cons`, `improvements`, `reviewer_comment`, `deterministic_checks` (JSONB), `created_at`.

This lets you compare quality across batches by querying `batch_id`. The batch summary printed to stdout (avg scores, top recurring cons) is a convenience view of the same data.

## Operational runbook addendum

After any migration that drops and recreates `rca.signals`, run `rca signal` immediately. The Phase 1 migration did this silently and left the signals table empty, breaking all `rca run` calls until `rca signal` was re-run manually. This is now documented in `CLAUDE.md`.

## Invariants

- The public CLI (`build`, `signal`, `run`, `mcp`) is unchanged.
- `replay` is additive — it calls the same `run_rca_graph` as `rca run`.
- `--dry-run` must exercise the full pipeline: investigation_loop → decision → evaluation → memory → record → review. The integration test enforces this.
- The reviewer prompt constant `REVIEWER_ALIGNMENT_PROMPT` must be audited before changes (per the project's prompt-audit rule).
