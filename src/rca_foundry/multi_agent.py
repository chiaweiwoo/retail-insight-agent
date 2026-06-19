from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from rca_foundry.config import DEFAULT_LLM_MAX_TOOL_ROUNDS
from rca_foundry.llm import (
    LLMSettings,
    build_chat_completion_kwargs,
    build_openai_compatible_client,
    load_llm_settings,
)
from rca_foundry.rca_tools import execute_tool, get_tool_schemas
from rca_foundry.render import render_markdown_document
from rca_foundry.run_logging import RunLogger


ClientFactory = Callable[[str], Any]


@dataclass(frozen=True)
class AnalystSpec:
    name: str
    focus: str
    tool_names: tuple[str, ...]
    system_prompt: str


@dataclass
class AnalystRunResult:
    name: str
    focus: str
    memo_markdown: str
    tool_calls: list[dict[str, Any]]


@dataclass
class ManagerRunResult:
    store_alias: str
    dt: str
    manager_report_markdown: str
    analyst_results: list[AnalystRunResult]


ANALYST_SPECS: tuple[AnalystSpec, ...] = (
    AnalystSpec(
        name="signal_analyst",
        focus="signal and sales baseline interpretation",
        tool_names=("get_signal_evidence", "get_sales_context"),
        system_prompt="""You are the signal analyst for a retail RCA team.

Focus only on signal validity, baseline comparisons, and recent sales shape.
Use only the tools provided to you.
Do not comment on stockout, discount, activity, weather, or peers unless they are explicitly in your tool evidence.
Use plain ASCII markdown.
Return sections:
1. Scope
2. Findings
3. Caveats
""",
    ),
    AnalystSpec(
        name="inventory_analyst",
        focus="stockout and availability assessment",
        tool_names=("get_stockout_context", "get_sales_context"),
        system_prompt="""You are the inventory analyst for a retail RCA team.

Focus on stockouts, availability pressure, and whether inventory issues likely explain part of the sales move.
Use only the tools provided to you.
Be explicit about cause vs consequence ambiguity.
Use plain ASCII markdown.
Return sections:
1. Scope
2. Findings
3. Caveats
""",
    ),
    AnalystSpec(
        name="pricing_activity_analyst",
        focus="pricing and promotional activity assessment",
        tool_names=("get_discount_context", "get_activity_context", "get_sales_context"),
        system_prompt="""You are the pricing and activity analyst for a retail RCA team.

Focus on discounting and promotional activity.
Assess whether pricing or promotion likely contributed to the sales move.
Use only the tools provided to you.
Use plain ASCII markdown.
Return sections:
1. Scope
2. Findings
3. Caveats
""",
    ),
    AnalystSpec(
        name="context_analyst",
        focus="calendar, weather, and peer context",
        tool_names=("get_calendar_weather_context", "get_peer_store_context", "get_sales_context"),
        system_prompt="""You are the context analyst for a retail RCA team.

Focus on calendar, weather, and peer comparison context.
Assess whether the move looks store-specific or broadly contextual.
Use only the tools provided to you.
Use plain ASCII markdown.
Return sections:
1. Scope
2. Findings
3. Caveats
""",
    ),
)


MANAGER_SYSTEM_PROMPT = """You are the RCA manager analyst.

You receive specialist memos from independent analysts.
Your job is to synthesize them into one evidence-backed RCA report.

Rules:
- Do not invent evidence beyond the specialist memos.
- Distinguish observed evidence from inference.
- Mention disagreements or ambiguity plainly.
- Prefer concise, practical reasoning.
- Use plain ASCII markdown.

Return sections:
1. Trigger
2. Likely Drivers
3. Evidence
4. Caveats
5. Suggested Next Checks
"""


def _default_client_factory(settings: LLMSettings) -> ClientFactory:
    def factory(_: str) -> Any:
        return build_openai_compatible_client(settings)

    return factory


def _run_tool_calling_specialist(
    spec: AnalystSpec,
    store_alias: str,
    dt: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    max_tool_rounds: int = DEFAULT_LLM_MAX_TOOL_ROUNDS,
) -> AnalystRunResult:
    subject = f"{store_alias}:{dt}"
    client = client_factory(spec.name)
    logger.log(
        actor_type="agent",
        actor_name=spec.name,
        action="started",
        subject=subject,
        source="system",
        details={"focus": spec.focus},
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": spec.system_prompt},
        {
            "role": "user",
            "content": (
                f"Analyze store {store_alias} on {dt}. "
                f"Your focus is {spec.focus}. Produce a short specialist memo."
            ),
        },
    ]
    tool_schemas = get_tool_schemas(spec.tool_names)
    executed_tool_calls: list[dict[str, Any]] = []

    for round_index in range(1, max_tool_rounds + 1):
        logger.log(
            actor_type="llm",
            actor_name=spec.name,
            action="completion_requested",
            subject=subject,
            source="llm",
            details={"round": round_index, "tool_names": list(spec.tool_names)},
        )
        response = client.chat.completions.create(
            **build_chat_completion_kwargs(settings, messages, tool_schemas)
        )
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            memo = getattr(message, "content", None) or ""
            logger.log(
                actor_type="llm",
                actor_name=spec.name,
                action="completion_finished",
                subject=subject,
                source="llm",
                details={"round": round_index, "content_preview": memo[:200]},
            )
            logger.log(
                actor_type="agent",
                actor_name=spec.name,
                action="completed",
                subject=subject,
                source="system",
                details={"tool_call_count": len(executed_tool_calls)},
            )
            return AnalystRunResult(
                name=spec.name,
                focus=spec.focus,
                memo_markdown=memo,
                tool_calls=executed_tool_calls,
            )

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": getattr(message, "content", None) or "",
            "tool_calls": [],
        }
        for tool_call in tool_calls:
            raw_arguments = tool_call.function.arguments or "{}"
            arguments = json.loads(raw_arguments)
            logger.log(
                actor_type="agent",
                actor_name=spec.name,
                action="tool_call_started",
                subject=subject,
                source="llm",
                details={"tool_name": tool_call.function.name, "arguments": arguments},
            )
            result = execute_tool(tool_call.function.name, arguments)
            logger.log(
                actor_type="tool",
                actor_name=tool_call.function.name,
                action="completed",
                subject=subject,
                source="tool",
                details={"called_by": spec.name, "result_preview": json.dumps(result)[:200]},
            )
            executed_tool_calls.append(
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": arguments,
                    "result": result,
                }
            )
            assistant_message["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": raw_arguments,
                    },
                }
            )
        messages.append(assistant_message)
        for tool_call in executed_tool_calls[-len(tool_calls) :]:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["name"],
                    "content": json.dumps(tool_call["result"]),
                }
            )

    raise RuntimeError(f"{spec.name} exceeded the maximum tool rounds ({max_tool_rounds}).")


def _run_manager_synthesis(
    store_alias: str,
    dt: str,
    analyst_results: list[AnalystRunResult],
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
) -> str:
    subject = f"{store_alias}:{dt}"
    client = client_factory("manager_analyst")
    memos = "\n\n".join(
        f"## {result.name}\nFocus: {result.focus}\n\n{result.memo_markdown}"
        for result in analyst_results
    )
    messages = [
        {"role": "system", "content": MANAGER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Synthesize the specialist memos for store {store_alias} on {dt}.\n\n"
                f"{memos}"
            ),
        },
    ]
    logger.log(
        actor_type="llm",
        actor_name="manager_analyst",
        action="completion_requested",
        subject=subject,
        source="llm",
        details={"specialist_count": len(analyst_results)},
    )
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(settings, messages, tools=None)
    )
    content = response.choices[0].message.content or ""
    logger.log(
        actor_type="llm",
        actor_name="manager_analyst",
        action="completion_finished",
        subject=subject,
        source="llm",
        details={"content_preview": content[:200]},
    )
    return content


def run_manager_analyst_pipeline(
    store_alias: str,
    dt: str,
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
    output_dir: Path | None = None,
) -> ManagerRunResult:
    settings = settings or load_llm_settings()
    client_factory = client_factory or _default_client_factory(settings)
    run_name = f"{store_alias}_{dt}"
    logger = RunLogger(run_name=run_name)
    subject = f"{store_alias}:{dt}"
    logger.log(
        actor_type="workflow",
        actor_name="manager_pipeline",
        action="started",
        subject=subject,
        source="system",
        details={"analyst_count": len(ANALYST_SPECS)},
    )

    def run_one(spec: AnalystSpec) -> AnalystRunResult:
        return _run_tool_calling_specialist(
            spec=spec,
            store_alias=store_alias,
            dt=dt,
            settings=settings,
            logger=logger,
            client_factory=client_factory,
        )

    with ThreadPoolExecutor(max_workers=len(ANALYST_SPECS)) as executor:
        future_map = {spec.name: executor.submit(run_one, spec) for spec in ANALYST_SPECS}
        results_by_name = {name: future.result() for name, future in future_map.items()}

    analyst_results = [results_by_name[spec.name] for spec in ANALYST_SPECS]
    logger.log(
        actor_type="workflow",
        actor_name="manager_pipeline",
        action="analysts_completed",
        subject=subject,
        source="system",
        details={
            "analysts": [result.name for result in analyst_results],
            "tool_call_counts": {result.name: len(result.tool_calls) for result in analyst_results},
        },
    )

    manager_report = _run_manager_synthesis(
        store_alias=store_alias,
        dt=dt,
        analyst_results=analyst_results,
        settings=settings,
        logger=logger,
        client_factory=client_factory,
    )
    logger.log(
        actor_type="workflow",
        actor_name="manager_pipeline",
        action="completed",
        subject=subject,
        source="system",
        details={"analyst_count": len(analyst_results)},
    )

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        specialist_dir = output_dir / "specialists"
        specialist_dir.mkdir(parents=True, exist_ok=True)
        for result in analyst_results:
            markdown_path = specialist_dir / f"{result.name}.md"
            html_path = specialist_dir / f"{result.name}.html"
            markdown_path.write_text(
                result.memo_markdown,
                encoding="utf-8",
            )
            html_path.write_text(
                render_markdown_document(
                    result.memo_markdown,
                    title=f"{result.name} memo for {store_alias} on {dt}",
                ),
                encoding="utf-8",
            )
        report_markdown_path = output_dir / "report.md"
        report_html_path = output_dir / "report.html"
        report_markdown_path.write_text(manager_report, encoding="utf-8")
        report_html_path.write_text(
            render_markdown_document(
                manager_report,
                title=f"RCA report for {store_alias} on {dt}",
            ),
            encoding="utf-8",
        )
        logger.write_artifacts(output_dir / "logs")
        payload = {
            "store_alias": store_alias,
            "dt": dt,
            "manager_report_markdown": manager_report,
            "analyst_results": [asdict(result) for result in analyst_results],
        }
        (output_dir / "manager_trace.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return ManagerRunResult(
        store_alias=store_alias,
        dt=dt,
        manager_report_markdown=manager_report,
        analyst_results=analyst_results,
    )
