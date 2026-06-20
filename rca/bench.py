from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from rca.config import AGENT_BENCHMARK_PATH, current_timestamp_sgt_label
from rca.agents import CoordinatorResult
from rca.tools import get_signal_evidence


@dataclass(frozen=True)
class BenchmarkScenario:
    scenario_id: str
    signal_strength: str  # high / medium / low — how strong the signal was
    expected_signal: str
    store_alias: str
    dt: str


SCENARIOS: tuple[BenchmarkScenario, ...] = (
    BenchmarkScenario("drop_high_h555_2024-05-16", "high", "drop", "h555", "2024-05-16"),
    BenchmarkScenario("drop_medium_m041_2024-05-09", "medium", "drop", "m041", "2024-05-09"),
    BenchmarkScenario("drop_low_l165_2024-05-16", "low", "drop", "l165", "2024-05-16"),
    BenchmarkScenario("lift_high_h235_2024-05-05", "high", "lift", "h235", "2024-05-05"),
    BenchmarkScenario("lift_medium_m041_2024-05-12", "medium", "lift", "m041", "2024-05-12"),
    BenchmarkScenario("lift_low_l185_2024-04-13", "low", "lift", "l185", "2024-04-13"),
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _result_payload(
    scenario: BenchmarkScenario,
    result: CoordinatorResult,
    run_started_at_sgt: str,
    model_name: str,
) -> dict[str, object]:
    signal = get_signal_evidence(scenario.store_alias, scenario.dt)
    return {
        "scenario": asdict(scenario),
        "run_started_at_sgt": run_started_at_sgt,
        "model_name": model_name,
        "signal_snapshot": signal,
        "analyst_count": len(result.analyst_results),
        "tool_call_count": int(sum(len(item.tool_calls) for item in result.analyst_results)),
        "analyst_results": [asdict(item) for item in result.analyst_results],
        "decision_card_markdown": result.decision_card_markdown,
        "critic_note_markdown": result.critic_note_markdown,
        "controller_note_markdown": result.controller_note_markdown,
        "report_markdown": result.coordinator_report_markdown,
    }


def _summary_row(
    scenario: BenchmarkScenario,
    result: CoordinatorResult,
) -> dict[str, object]:
    signal = get_signal_evidence(scenario.store_alias, scenario.dt)
    return {
        "scenario_id": scenario.scenario_id,
        "expected_signal": scenario.expected_signal,
        "observed_signal": signal["signal_label"],
        "store_alias": scenario.store_alias,
        "dt": scenario.dt,
        "analyst_count": len(result.analyst_results),
        "tool_call_count": int(sum(len(item.tool_calls) for item in result.analyst_results)),
    }


def _build_manifest_markdown(
    run_dir: Path,
    timestamp_label: str,
    model_name: str,
    summary_rows: list[dict[str, object]],
) -> str:
    lines = [
        "# RCA Agent Benchmark Run",
        "",
        f"- run timestamp (SGT): `{timestamp_label}`",
        f"- model: `{model_name}`",
        f"- scenario count: `{len(summary_rows)}`",
        "",
        "## Scenario Outputs",
        "",
        "| scenario_id | expected_signal | observed_signal | store_alias | dt | analysts | tool_call_count | decision_card | report_html | run_trace | run_log |",
        "| --- | --- | --- | --- | --- | ---: | ---: | --- | --- | --- | --- |",
    ]
    for row in summary_rows:
        scenario_dir = run_dir / str(row["scenario_id"])
        decision_card_path = scenario_dir / "decision_card.html"
        report_html_path = scenario_dir / "report.html"
        trace_path = scenario_dir / "run_trace.json"
        run_log_path = scenario_dir / "run_log.md"
        lines.append(
            "| {scenario_id} | {expected_signal} | {observed_signal} | {store_alias} | {dt} | {analyst_count} | {tool_call_count} | "
            "[decision_card.html]({decision_card}) | [report.html]({report_html}) | [run_trace.json]({trace}) | [run_log.md]({run_log}) |".format(
                scenario_id=row["scenario_id"],
                expected_signal=row["expected_signal"],
                observed_signal=row["observed_signal"],
                store_alias=row["store_alias"],
                dt=row["dt"],
                analyst_count=row["analyst_count"],
                tool_call_count=row["tool_call_count"],
                decision_card=decision_card_path.relative_to(run_dir).as_posix(),
                report_html=report_html_path.relative_to(run_dir).as_posix(),
                trace=trace_path.relative_to(run_dir).as_posix(),
                run_log=run_log_path.relative_to(run_dir).as_posix(),
            )
        )
    lines.extend(
        [
            "",
            "## Quick Checks",
            "",
            "- compare `expected_signal` vs `observed_signal` for trigger alignment",
            "- review `tool_call_count` for prompt/tool efficiency drift",
            "- inspect the decision card first, then drill down into report, trace, and run log",
        ]
    )
    return "\n".join(lines) + "\n"


def run_benchmark(client_factory=None) -> None:
    from rca.llm import load_llm_settings, LLMSettings
    from rca.agents import run_coordinator

    if client_factory is not None:
        settings = LLMSettings(
            api_key="dry-run",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        )
    else:
        settings = load_llm_settings()
    timestamp_label = current_timestamp_sgt_label()
    run_dir = AGENT_BENCHMARK_PATH / timestamp_label
    run_dir.mkdir(parents=True, exist_ok=True)

    summary_rows: list[dict[str, object]] = []
    for scenario in SCENARIOS:
        scenario_dir = run_dir / scenario.scenario_id
        result = run_coordinator(
            store_alias=scenario.store_alias,
            dt=scenario.dt,
            settings=settings,
            client_factory=client_factory,
            output_dir=scenario_dir,
        )
        payload = _result_payload(
            scenario=scenario,
            result=result,
            run_started_at_sgt=timestamp_label,
            model_name=settings.model,
        )
        _write_json(scenario_dir / "trace.json", payload)
        summary_rows.append(_summary_row(scenario, result))

    _write_json(run_dir / "manifest.json", summary_rows)
    _write_text(
        run_dir / "README.md",
        _build_manifest_markdown(run_dir, timestamp_label, settings.model, summary_rows),
    )
    print(f"Saved benchmark run to {run_dir}")
