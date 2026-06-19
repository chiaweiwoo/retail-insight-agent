from __future__ import annotations

import json

from rca.evaluator import deterministic_faithfulness_check, evaluate_benchmark
from rca.llm import LLMSettings
from rca.stubclient import stub_client_factory


def test_deterministic_faithfulness_check_flags_unsupported_numbers() -> None:
    result = deterministic_faithfulness_check(
        [
                {
                    "name": "sales_analyst",
                    "memo_markdown": (
                        "## Assessment\n"
                        "- key_numbers: baseline 100, observed 80\n"
                    ),
                "tool_calls": [
                    {
                        "name": "get_signal_evidence",
                        "result": {
                            "baseline": 100,
                            "observed": 80,
                        },
                    }
                ],
            },
            {
                "name": "ops_analyst",
                "memo_markdown": (
                    "## Assessment\n"
                    "- key_numbers: stockout 9, pressure 0.4\n"
                ),
                "tool_calls": [
                    {
                        "name": "get_stockout_context",
                        "result": {
                            "stockout": 4,
                            "pressure": 0.4,
                        },
                    }
                ],
            },
        ]
    )

    assert result.checked_analysts == 2
    assert result.supported_analysts == 1
    assert result.unsupported_analysts == 1
    assert result.unsupported_details[0]["analyst"] == "ops_analyst"


def test_evaluate_benchmark_writes_report(tmp_path) -> None:
    run_dir = tmp_path / "bench_run"
    scenario_dir = run_dir / "drop_high_h555_2024-05-16"
    scenario_dir.mkdir(parents=True)
    trace = {
        "planner": {
            "planning_inputs": {
                "signal_evidence": {
                    "signal_label": "drop",
                }
            }
        },
        "decision_card_markdown": "## Decision Card\n- confidence: low\n- action: none - monitor",
        "coordinator_report_markdown": "## Trigger\nDrop\n\n## Likely Drivers\n1. [inconclusive / low] Unknown",
        "critic_note_markdown": "## Claim Audit\n- keep",
        "analyst_results": [
            {
                "name": "sales_analyst",
                "memo_markdown": "## Assessment\n- key_numbers: baseline 100, observed 80",
                "tool_calls": [
                    {
                        "name": "get_signal_evidence",
                        "result": {"baseline": 100, "observed": 80},
                    }
                ],
            }
        ],
    }
    (scenario_dir / "coordinator_trace.json").write_text(
        json.dumps(trace, indent=2),
        encoding="utf-8",
    )

    payload = evaluate_benchmark(
        run_dir=run_dir,
        settings=LLMSettings(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        ),
        client_factory=stub_client_factory,
    )

    assert payload["scenario_count"] == 1
    assert payload["signal_match_count"] == 1
    assert (run_dir / "eval_report.json").exists()
    assert (run_dir / "eval_report.md").exists()
