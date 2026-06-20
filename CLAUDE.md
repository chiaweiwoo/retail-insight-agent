# CLAUDE.md

Read `README.md` first for the current workflow.

## Useful Commands

```bash
uv run python -m rca.cli build
uv run python -m rca.cli analyze
uv run python -m rca.cli profile
uv run python -m rca.cli run --store h555 --dt 2024-05-16 --dry-run --full
uv run python -m rca.cli run --store h555 --dt 2024-05-16 --dry-run --reflect  # adds reflection pass
uv run python -m rca.cli bench
uv run python -m rca.cli eval --dry-run
uv run python -m rca.cli story --run-dir data/analysis/agent_benchmark_runs/<run_folder>
uv run python -m rca.cli runs
uv run python -m rca.cli distil --store h555          # generate store memory profile
uv run python -m rca.cli distil                       # distil all stores with history
uv run python -m rca.cli reset-memory --store h555    # delete one store's profile
uv run python -m rca.cli reset-memory --all           # delete all profiles
uv run python -m rca.cli mcp                          # start the FastMCP server
```

## Important Behavior

- `rca run` prints the decision card by default.
- `--full` also prints the drill-down RCA.
- `--dry-run` uses the deterministic stub client and should exercise the whole pipeline.
- `rca story` reads a saved trace and writes root-level story report files.
- `sale_amount` and `hours_sale` are normalized sales amounts from the source dataset, not currency. Prefer `sales amount`.
- **Model Routing**: Specialists run on the fast model (e.g., flash), while synthesis/oversight (critic, coordinator, controller, slt) run on the deep model (e.g., pro).
- **Deterministic Sanitizer**: The `sanitize` node uses no LLM calls. It runs strictly once at the write boundary before pushing to Supabase.

## Artifacts & Datastores

Non-quick runs write decision cards, run traces, specialist memos, and logs to `data/analysis/agent_benchmark_runs/`.

**Datastores (Supabase is the System of Record)**:
- Supabase: Primary read/write target for operations (`rca_` prefixed tables).
- `data/rca.duckdb`: Kept for ETL only (aggregating parquet data before pushing to Supabase).
- `data/runs.duckdb`: Legacy log database (deprecating).

## Sandbox Caveats

The local dataset contains only 15 stores (from a 5-city scope). "Peer group" comparisons are statistically noisy. Do not let agents over-index on peer comparisons without acknowledging this limitation.
