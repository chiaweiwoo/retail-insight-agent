# Retail Insight Agent

Retail RCA playground built on a local DuckDB evidence store, with a calibration-first multi-agent workflow on top.

The current shape is:

1. Build clean daily store facts in DuckDB.
2. Precompute sales drop/lift signals.
3. Run a selective analyst workflow per store-day.
4. Produce a decision card, drill-down RCA, trace, and logs.
5. Store prior outcomes so later runs can tell first-time noise from recurring patterns.
6. Evaluate benchmark runs with deterministic faithfulness checks plus an LLM judge.

## Quick Start

```bash
uv sync
uv run python -m rca.cli build
uv run python -m rca.cli analyze
uv run python -m rca.cli profile
uv run python -m rca.cli run --store h555 --dt 2024-05-16 --full
uv run python -m rca.cli runs
```

Dry-run mode exercises the whole workflow without API calls:

```bash
uv run python -m rca.cli run --store h555 --dt 2024-05-16 --dry-run --full
```

## Commands

| Command | What it does |
| --- | --- |
| `uv run python -m rca.cli build` | Ingest raw parquet into `data/rca.duckdb` and validate row counts |
| `uv run python -m rca.cli analyze` | Precompute signal CSVs and trigger grids under `data/analysis/` |
| `uv run python -m rca.cli profile` | Build `data/context_pack.json` and `data/context_pack.md` |
| `uv run python -m rca.cli run --store S --dt D [--dry-run] [--full]` | Run one RCA workflow; prints decision card by default |
| `uv run python -m rca.cli bench` | Run the 6 fixed benchmark scenarios |
| `uv run python -m rca.cli eval [--run-dir PATH] [--dry-run]` | Evaluate a benchmark run directory |
| `uv run python -m rca.cli runs` | Show recent run history from `data/runs.duckdb` |
| `uv run python -m rca.cli dashboard` | Rebuild the static dashboard HTML |
| `uv run python -m rca.cli export` | Refresh the UI evidence JSON |

## Runtime Design

The workflow is selective and calibration-first.

```mermaid
flowchart TD
    A["Input: store_alias + dt"] --> B["context pack + prior RCA lookup"]
    B --> C["plan_specialists"]
    C --> D["sales_analyst"]
    C --> E["ops_analyst (if stockout signal)"]
    C --> F["commercial_analyst (if promo/discount signal)"]
    C --> G["market_analyst"]
    C --> H["research_analyst (optional, off by default)"]
    D --> I["critic"]
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J["coordinator"]
    J --> K["finance_controller"]
    K --> L["slt_brief"]
    L --> M["record outcome"]
    M --> N["artifacts + run logs"]
```

![Agent Runtime DAG](/C:/Users/chiaw/OneDrive/Desktop/playground/retail_insight_agent/docs/images/agent_runtime_dag.svg)

## Agent Roles

| Node | Role | Tool access |
| --- | --- | --- |
| `plan_specialists` | Cheap local planner that decides which analysts to run | local evidence functions only |
| `sales_analyst` | Confirms trigger magnitude and baseline comparisons | `get_signal_evidence`, `get_sales_context` |
| `ops_analyst` | Checks stockout and availability pressure | `get_stockout_context`, `get_sales_context` |
| `commercial_analyst` | Checks discount and activity effects; flags margin risk honestly | `get_discount_context`, `get_activity_context`, `get_sales_context` |
| `market_analyst` | Checks calendar, weather, and peer context | `get_calendar_weather_context`, `get_peer_store_context`, `get_sales_context` |
| `research_analyst` | Optional retrospective news search | `search_news` |
| `critic` | Downgrades weak claims and flags correlation-as-cause | no direct tools |
| `coordinator_analyst` | Synthesizes analyst memos into one RCA | no direct tools |
| `finance_controller` | Adds materiality, margin-risk, and one-off vs structural framing | no direct tools |
| `slt_brief` | Compresses the RCA into the decision card | no direct tools |
| `evaluator` | Offline judge for benchmark quality | no direct tools |

## Calibration Rules

- Outputs are correlational RCA, not proof of causality.
- Every specialist ends with an `Assessment` block.
- Confidence vocabulary is fixed: `high`, `medium`, `low`.
- The critic is part of the run and improves the current output.
- The evaluator is separate and scores the system offline.

## Data Layout

- `data/rca.duckdb`: daily store facts and dimensions
- `data/context_pack.json` / `.md`: compact grounding pack built from local data
- `data/analysis/`: signal summaries, trigger grids, benchmark outputs
- `data/runs.duckdb`: run log plus `rca_outcome` memory table

## Run Artifacts

Each non-quick `rca run` writes a timestamped folder under `data/analysis/agent_benchmark_runs/` with:

- `decision_card.md` and `.html`
- `report.md` and `.html`
- `critique.md` and `.html`
- `controller_note.md` and `.html`
- `run_trace.json`
- `run_log.jsonl`
- `run_log.md`
- `specialists/*.md` and `.html`

## Evaluation

`rca eval` writes:

- `eval_report.json`
- `eval_report.md`

The evaluator combines:

- deterministic faithfulness checks against analyst tool outputs
- expected signal vs observed signal
- an LLM judge rubric for groundedness, calibration, actionability, conciseness, and causal honesty

## Notes

- Research is off by default because it adds external noise and cost.
- The context pack stays conservative about anonymized IDs.
- The decision card is the primary output; the full RCA is the drill-down.
