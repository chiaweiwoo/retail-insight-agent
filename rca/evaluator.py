from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import re
from typing import Any, Callable

from rca.bench import SCENARIOS
from rca.llm import (
    LLMSettings,
    build_chat_completion_kwargs,
    build_openai_compatible_client,
    load_llm_settings,
)


ClientFactory = Callable[[str], Any]


EVALUATOR_SYSTEM_PROMPT = """You are an RCA quality judge.

Score the run on nine dimensions from 1 to 5:
- groundedness
- calibration
- actionability
- conciseness
- causal_honesty
- time_to_decision
- format_compliance
- procedure_transparency
- restraint

Rules:
- judge only the supplied artifacts
- do not reward fancy prose over honesty
- prefer restrained, evidence-backed output
- return valid JSON with exactly these 9 numeric keys + 1 string key: groundedness, calibration, actionability, conciseness, causal_honesty, time_to_decision, format_compliance, procedure_transparency, restraint, executive_pov
"""


@dataclass(frozen=True)
class FaithfulnessResult:
    checked_analysts: int
    supported_analysts: int
    unsupported_analysts: int
    unsupported_details: list[dict[str, Any]]


@dataclass(frozen=True)
class EvaluatedScenario:
    scenario_id: str
    expected_signal: str
    observed_signal: str
    signal_match: bool
    faithfulness: FaithfulnessResult
    judge_scores: dict[str, Any]


def deterministic_faithfulness_check(analyst_results: list[dict[str, Any]]) -> FaithfulnessResult:
    unsupported_details: list[dict[str, Any]] = []
    checked = 0
    supported = 0

    for result in analyst_results:
        tool_calls = result.get("tool_calls") or []
        if not tool_calls:
            continue
        checked += 1
        memo_text = str(result.get("memo_markdown", ""))
        cited_numbers = _extract_numbers(_assessment_key_numbers_text(memo_text))
        source_numbers = _extract_numbers(json.dumps(tool_calls, ensure_ascii=False))
        missing = sorted(number for number in cited_numbers if number not in source_numbers)
        if missing:
            unsupported_details.append(
                {
                    "analyst": result.get("name", "unknown"),
                    "missing_numbers": missing,
                }
            )
        else:
            supported += 1

    return FaithfulnessResult(
        checked_analysts=checked,
        supported_analysts=supported,
        unsupported_analysts=len(unsupported_details),
        unsupported_details=unsupported_details,
    )


def evaluate_benchmark(
    run_dir: Path,
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    settings = settings or load_llm_settings()
    client_factory = client_factory or _default_client_factory(settings)
    scenario_results: list[EvaluatedScenario] = []

    scenario_dirs = _resolve_scenario_dirs(run_dir)
    for scenario in SCENARIOS:
        scenario_dir = scenario_dirs.get(scenario.scenario_id)
        if scenario_dir is None:
            continue
        trace_path = scenario_dir / "coordinator_trace.json"
        trace = json.loads(trace_path.read_text(encoding="utf-8"))
        faithfulness = deterministic_faithfulness_check(trace.get("analyst_results", []))
        judge_scores = _judge_scenario(trace, scenario.expected_signal, client_factory, settings)
        observed_signal = str(trace["planner"]["planning_inputs"]["signal_evidence"]["signal_label"])
        scenario_results.append(
            EvaluatedScenario(
                scenario_id=scenario.scenario_id,
                expected_signal=scenario.expected_signal,
                observed_signal=observed_signal,
                signal_match=(observed_signal == scenario.expected_signal),
                faithfulness=faithfulness,
                judge_scores=judge_scores,
            )
        )

    payload = {
        "run_dir": str(run_dir),
        "scenario_count": len(scenario_results),
        "signal_match_count": sum(1 for result in scenario_results if result.signal_match),
        "faithfulness_supported_count": sum(
            result.faithfulness.supported_analysts for result in scenario_results
        ),
        "faithfulness_unsupported_count": sum(
            result.faithfulness.unsupported_analysts for result in scenario_results
        ),
        "scenarios": [
            {
                **asdict(result),
                "faithfulness": asdict(result.faithfulness),
            }
            for result in scenario_results
        ],
    }
    (run_dir / "eval_report.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "eval_report.md").write_text(
        _render_eval_markdown(payload),
        encoding="utf-8",
    )
    return payload


def _resolve_scenario_dirs(run_dir: Path) -> dict[str, Path]:
    """Locate scenario subdirs inside a bench run or a single run dir.

    Bench layout:  <run_dir>/<scenario_id>/coordinator_trace.json
    Single layout: <run_dir>/coordinator_trace.json
    """
    direct_trace = run_dir / "coordinator_trace.json"
    if direct_trace.exists():
        return {run_dir.name: run_dir}

    # Bench layout — scan for any subdir with a coordinator_trace.json
    scenario_dirs: dict[str, Path] = {}
    for child in sorted(run_dir.iterdir()):
        if not child.is_dir():
            continue
        trace = child / "coordinator_trace.json"
        if trace.exists():
            scenario_dirs[child.name] = child

    if not scenario_dirs:
        raise FileNotFoundError(
            f"No coordinator_trace.json found in {run_dir} or its subdirectories. "
            "Run 'rca bench' first, then pass the bench run directory with --run-dir."
        )
    return scenario_dirs


def _judge_scenario(
    trace: dict[str, Any],
    expected_signal: str,
    client_factory: ClientFactory,
    settings: LLMSettings,
) -> dict[str, Any]:
    client = client_factory("evaluator")
    messages = [
        {"role": "system", "content": EVALUATOR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Expected signal: {expected_signal}\n"
                f"Observed signal: {trace['planner']['planning_inputs']['signal_evidence']['signal_label']}\n\n"
                f"Decision card:\n{trace['decision_card_markdown']}\n\n"
                f"Report:\n{trace['coordinator_report_markdown']}\n\n"
                f"Critic note:\n{trace['critic_note_markdown']}\n"
            ),
        },
    ]
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(settings, messages, tools=None)
    )
    content = response.choices[0].message.content or "{}"
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_response": content}


def _default_client_factory(settings: LLMSettings) -> ClientFactory:
    def factory(_: str) -> Any:
        return build_openai_compatible_client(settings)

    return factory


def _assessment_key_numbers_text(memo_text: str) -> str:
    match = re.search(r"^- key_numbers:\s*(.+)$", memo_text, re.MULTILINE)
    return match.group(1) if match else ""


def _extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"-?\d+(?:\.\d+)?%?", text))


def _render_eval_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Evaluation Report",
        "",
        f"- run_dir: `{payload['run_dir']}`",
        f"- scenarios: `{payload['scenario_count']}`",
        f"- signal matches: `{payload['signal_match_count']}`",
        f"- unsupported analyst checks: `{payload['faithfulness_unsupported_count']}`",
        "",
        "| scenario_id | signal_match | checked_analysts | unsupported_analysts | groundedness | calibration | actionability | time_to_decision | format_compliance | procedure_transparency | restraint |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scenario in payload["scenarios"]:
        scores = scenario["judge_scores"]
        lines.append(
            "| {scenario_id} | {signal_match} | {checked} | {unsupported} | {groundedness} | {calibration} | {actionability} | {time_to_decision} | {format_compliance} | {procedure_transparency} | {restraint} |".format(
                scenario_id=scenario["scenario_id"],
                signal_match="yes" if scenario["signal_match"] else "no",
                checked=scenario["faithfulness"]["checked_analysts"],
                unsupported=scenario["faithfulness"]["unsupported_analysts"],
                groundedness=scores.get("groundedness", "n/a"),
                calibration=scores.get("calibration", "n/a"),
                actionability=scores.get("actionability", "n/a"),
                time_to_decision=scores.get("time_to_decision", "n/a"),
                format_compliance=scores.get("format_compliance", "n/a"),
                procedure_transparency=scores.get("procedure_transparency", "n/a"),
                restraint=scores.get("restraint", "n/a"),
            )
        )
        executive_pov = scores.get("executive_pov", "n/a")
        lines.append(f"  - **Executive POV**: {executive_pov}")
    lines.append("")
    return "\n".join(lines)
