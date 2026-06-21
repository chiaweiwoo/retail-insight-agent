# ADR 0004: City Simulation and Self-Review Harness

## Status

Implemented.

## Context

After the Level 5 learning-mode refactor, the project needed two practical safeguards:

1. A reliable end-to-end test path that exercises the graph without calling a real LLM.
2. A way to rerun every triggered date for one city, accumulate memory chronologically, and compare RCA quality across batches.

The public CLI was later simplified so agents do not pass unnecessary or dangerous flags.

## Decision 1: Stub Client Stays Internal

The deterministic stub client remains available to tests through Python injection, not through a public CLI flag.

The graph integration test exercises:

```text
investigation_loop -> decision -> evaluation -> memory -> record
```

This keeps CI useful without exposing a dry-run flag to humans or agents.

## Decision 2: Simulation Is Full-City, Cold-Start, And Reviewed

`rca simulate --city N` always deletes all city outputs and caches first, then processes every triggered `drop` and `lift` date oldest to latest.

The cold-start reset is mandatory, not optional: reproducibility and batch comparability require a clean slate each time. If you want to accumulate on top of existing memory, use `rca run` per date manually.

Simulation always runs the alignment reviewer after each date and stores review rows in `rca.simulate_review`.

There are no public `--limit`, `--no-review`, or `--batch-id` flags. Batch IDs are generated internally with a timestamp.

## Decision 3: Review Storage

`rca.simulate_review` stores one row per simulated city/date within a generated batch.

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

This lets us compare quality across simulation batches without adding more public CLI switches.

## Invariants

- Public CLI is intentionally small: `build`, `signal`, `run`, `simulate`, `mcp`.
- `run` accepts only `--city` and `--date`.
- `simulate` accepts only `--city`. Reset is always on.
- `simulate` uses the same `run_rca_graph` path as `rca run`.
- Stub execution remains internal to tests.
- The reviewer prompt must be audited before changes.
