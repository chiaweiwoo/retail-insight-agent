# ADR 0004: City Replay and Self-Review Harness

## Status

Implemented.

## Context

After the Level 5 learning-mode refactor, the project needed two practical safeguards:

1. A reliable end-to-end test path that exercises the graph without calling a real LLM.
2. A way to replay every triggered date for one city, accumulate memory chronologically, and compare RCA quality across batches.

The public CLI was later simplified so agents do not pass unnecessary or dangerous flags.

## Decision 1: Stub Client Stays Internal

The deterministic stub client remains available to tests through Python injection, not through a public CLI flag.

The graph integration test exercises:

```text
investigation_loop -> decision -> evaluation -> memory -> record
```

This keeps CI useful without exposing `--dry-run` to humans or agents.

## Decision 2: Replay Is Full-City And Reviewed

`rca replay --city N` processes all triggered `drop` and `lift` signal dates for that city from oldest to latest.

Replay always runs the alignment reviewer after each date and stores review rows in `rca.replay_review`.

There is no public `--limit`, `--no-review`, or `--batch-id` flag. Batch IDs are generated internally with a timestamp.

## Decision 3: Reset Is Explicit

Plain replay is non-destructive:

```bash
rca replay --city 0
```

Destructive cold-start replay is explicit:

```bash
rca replay --city 0 --reset
```

`--reset` deletes city rows from:

- `outcomes`
- `events`
- `completions`
- `memory`
- `evidence_cache`
- `external_events`

Signals and base tables are never touched by replay reset.

## Decision 4: Replay Review Storage

`rca.replay_review` stores one row per replayed city/date within a generated batch.

Important fields:

- `batch_id`
- `run_id`
- `city_id`
- `dt`
- `signal_label`
- `eval_score`
- `eval_passed`
- `alignment_score`
- `alignment_label`
- `pros`
- `cons`
- `improvements`
- `reviewer_comment`
- `deterministic_checks`

This lets us compare quality across replay batches without adding more public CLI switches.

## Invariants

- Public CLI is intentionally small: `build`, `signal`, `run`, `replay`, `mcp`.
- `run` accepts only `--city` and `--date`.
- `replay` accepts only `--city` and optional `--reset`.
- Replay uses the same `run_rca_graph` path as `rca run`.
- Stub execution remains internal to tests.
- The reviewer prompt must be audited before changes.
