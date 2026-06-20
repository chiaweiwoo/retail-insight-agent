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
uv run python -m rca.cli story --run-dir data/analysis/agent_benchmark_runs/<run_folder>
uv run python -m rca.cli runs
uv run python -m rca.cli distil --store h555          # generate store memory profile
uv run python -m rca.cli distil                       # distil all stores with history
uv run python -m rca.cli reset-memory --store h555    # delete one store's profile
uv run python -m rca.cli reset-memory --all           # delete all profiles
```

## Important Behavior

- `rca run` prints the decision card by default.
- `--full` also prints the drill-down RCA.
- `--dry-run` uses the deterministic stub client and should exercise the whole pipeline.
- Research is gated off by default.
- `rca story` is a post-run report rendering step. It reads a saved trace and writes root-level story report files.
- `sale_amount` and `hours_sale` are normalized sales amounts from the source dataset, not literal units and not currency revenue. Prefer phrases like `sales amount`, `normalized sales amount`, or `relative sales level`.
- Do not call store prefixes (`h/m/l`) tiers unless the text explicitly says they are only opaque prefix groupings.
- **Sandbox vs Production Scale (Crucial Context)**: The underlying raw dataset is `FreshRetailNet-50K` (898 stores, 18 cities, 50,000 series, heavily normalized metrics, sales could be in millions in reality). However, our local DuckDB database is a tiny sandbox subset of only **15 stores** spanning 90 days. 
  - **WARNING**: Because the local dataset only has 15 stores, "peer group" comparisons (e.g. comparing a store to others sharing the same prefix) are statistically noisy and often meaningless. A peer group might only have 2-4 stores. Do not let the AI agents over-index on peer comparisons without acknowledging this limitation.

## Artifacts

Non-quick runs write:

- decision card
- RCA report
- critic note
- finance controller note
- run trace
- run logs
- specialist memos
- optional story report under `output/story_reports/<run_folder>/`

## Local Datastores

- `data/rca.duckdb`: analytical evidence store
- `data/runs.duckdb`: run logs and `rca_outcome` memory

## Scenario Notes

The six fixed benchmark scenarios should stay stable unless the benchmark definition changes.

Ad hoc story-report examples can be selected separately. The current exploratory negative candidate is:

```text
l165 2024-06-06
```

Reason: it has a strong trailing-7-day drop, but same-weekday baseline is nearly normal, so it tests whether the RCA can identify a likely window-composition artifact instead of over-explaining the drop.
