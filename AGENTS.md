# AGENTS.md

Working notes for the RCA agent system. Runtime behavior should match `README.md`.

## Guardrails

- Calibration matters more than eloquence.
- Every node must change the output in a visible way.
- Claims must stay tied to evidence we actually have.
- Margin is a risk lens here, not a computed metric.
- The evaluator is separate from the critic.

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

## Logging Expectations

Each run folder should be inspectable on its own:

- `run_trace.json`
- `run_log.jsonl`
- `run_log.md`
- node artifacts

## Still Out Of Scope

- MCP runtime
- Skills runtime
- Product/category drilldown
- Customer analysis
- Production serving stack
