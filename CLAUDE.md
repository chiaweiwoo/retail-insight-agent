# CLAUDE.md

Read `README.md` first for the current workflow.

## Useful Commands

```bash
uv run python -m rca.cli build
uv run python -m rca.cli analyze
uv run python -m rca.cli profile
uv run python -m rca.cli run --store h555 --dt 2024-05-16 --dry-run --full
uv run python -m rca.cli bench
uv run python -m rca.cli eval --dry-run
uv run python -m rca.cli runs
```

## Important Behavior

- `rca run` prints the decision card by default.
- `--full` also prints the drill-down RCA.
- `--dry-run` uses the deterministic stub client and should exercise the whole pipeline.
- Research is gated off by default.

## Artifacts

Non-quick runs write:

- decision card
- RCA report
- critic note
- finance controller note
- run trace
- run logs
- specialist memos

## Local Datastores

- `data/rca.duckdb`: analytical evidence store
- `data/runs.duckdb`: run logs and `rca_outcome` memory
