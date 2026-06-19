# AGENTS.md

Working notes for the RCA agent system. Runtime behavior should match `README.md`.

## Guardrails

- Calibration matters more than eloquence.
- Every node must change the output in a visible way.
- Claims must stay tied to evidence we actually have.
- Margin is a risk lens here, not a computed metric.
- The evaluator is separate from the critic.

## Data Scale Limitations (Sandbox vs Production)

- **The Dataset**: The underlying source is `FreshRetailNet-50K` (898 stores, 18 cities, 50,000 series). Sales units are heavily normalized and actual figures could be in the millions.
- **The Sandbox**: Our local DuckDB environment contains a tiny subset of **only 15 stores**.
- **The Rule**: Because the local dataset only has 15 stores, "peer group" comparisons (e.g. comparing a store to others with the same prefix) are statistically noisy and often meaningless. A peer group might only contain 2-4 stores. The Critic and Analysts must acknowledge this small sample size and avoid over-indexing on peer outperformance/underperformance as a definitive root cause.

## Pipeline

1. Build compact grounding context from DuckDB.
2. Read prior RCA outcomes for the store.
3. Plan which specialists to dispatch.
4. Run selected specialists in parallel.
5. Run one critic pass.
6. Synthesize with the coordinator.
7. Add finance-controller framing.
8. Produce the SLT decision card.
9. Record structured outcome memory.
10. Save trace and run logs.
11. Optionally generate a reader-facing story report from the saved trace.

## Tool Access

| Agent | Tools |
| --- | --- |
| `sales_analyst` | `get_signal_evidence`, `get_sales_context` |
| `ops_analyst` | `get_stockout_context`, `get_sales_context` |
| `commercial_analyst` | `get_discount_context`, `get_activity_context`, `get_sales_context` |
| `market_analyst` | `get_calendar_weather_context`, `get_peer_store_context`, `get_sales_context` |
| `research_analyst` | `search_news` |
| planner | local evidence functions only |
| critic / coordinator / controller / slt / evaluator | no direct tools |

## Report Outputs

`rca run` is the evidence workflow. It saves the raw RCA artifacts in the timestamped run folder.

`rca story` is a post-run presentation step. It reads `run_trace.json` and writes a cleaner reader-facing report to:

```text
output/story_reports/<run_folder>/story_report.md
output/story_reports/<run_folder>/story_report.html
```

The story report should explain the sequence of reasoning:

1. why the store-day triggered
2. what each selected analyst checked
3. which tools were used
4. what the critic challenged
5. what decision survived the critique

Keep the story report grounded. It may polish language, but it must not invent evidence beyond the trace.

## Logging Expectations

Each run folder should be inspectable on its own:

- `run_trace.json`
- `run_log.jsonl`
- `run_log.md`
- node artifacts

Logs should remain useful for auditing:

- timestamped actions
- node or agent name
- tool calls
- whether an action was deterministic code or LLM output
- artifact paths produced by the run

## Scenario Selection

Keep benchmark scenarios separate from exploratory storytelling examples.

The fixed benchmark set is for regression quality. It should not change casually.

Exploratory examples are allowed when we want a better report demo. Prefer negative cases when they expose actual RCA tension, especially:

- drop trigger is strong
- same-weekday baseline exists
- stockout or promotion context conflicts with the simple sales signal
- peer context changes the interpretation

Current exploratory negative candidate:

```text
l165 2024-06-06
```

Reason: the trailing-7-day signal is a clear drop, but same-weekday baseline is nearly normal. That makes it useful for testing whether the agent can say "this alert may be a window artifact" instead of forcing a cause.

## Still Out Of Scope

- MCP runtime
- Skills runtime
- Product/category drilldown
- Customer analysis
- Production serving stack
