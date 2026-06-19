from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from rca.config import (
    ASSESSMENT_FORMAT,
    CONFIDENCE_VOCAB,
    DEFAULT_LLM_MAX_TOOL_ROUNDS,
    LOG_DB_PATH,
)
from rca.context import build_context_preamble
from rca.llm import (
    LLMSettings,
    build_chat_completion_kwargs,
    build_openai_compatible_client,
    load_llm_settings,
)
from rca.tools import execute_tool, get_tool_schemas
from rca.report import render_markdown_document
from rca.runlog import RunLogger


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
class CoordinatorResult:
    store_alias: str
    dt: str
    coordinator_report_markdown: str
    critic_note_markdown: str
    analyst_results: list[AnalystRunResult]


def _analyst_prompt(role: str, domain_instructions: str) -> str:
    return f"""You are the {role} for a retail RCA team.

{domain_instructions}

{CONFIDENCE_VOCAB}

Use only the tools provided to you. Use plain ASCII markdown. Return sections:
1. Scope
2. Findings
3. Caveats
4. Assessment (required — see format below)

{ASSESSMENT_FORMAT}

If your domain shows nothing material, return verdict "inconclusive" and confidence "low"
rather than padding the findings section. Concise and honest is better than long and inflated.
"""


ANALYST_SPECS: tuple[AnalystSpec, ...] = (
    AnalystSpec(
        name="sales_analyst",
        focus="sales performance — confirm signal magnitude and baseline comparison",
        tool_names=("get_signal_evidence", "get_sales_context"),
        system_prompt=_analyst_prompt(
            role="Sales Analyst",
            domain_instructions=(
                "Confirm whether the sales move is real and how large it is. "
                "Compare current sales against trailing 7-day average, previous day, and same-weekday baselines. "
                "Describe the recent sales trend shape. "
                "Do not comment on stockouts, discounts, promotions, weather, or peers "
                "unless they appear directly in your tool output."
            ),
        ),
    ),
    AnalystSpec(
        name="ops_analyst",
        focus="operations — stockout and product availability assessment",
        tool_names=("get_stockout_context", "get_sales_context"),
        system_prompt=_analyst_prompt(
            role="Operations Analyst",
            domain_instructions=(
                "Assess whether stockouts or product availability issues contributed to the sales move. "
                "Look at stockout hours, stockout rates by severity, and peak hourly pressure. "
                "Be explicit about cause vs consequence ambiguity — stockouts can cause drops, "
                "but drops can also precede stockouts."
            ),
        ),
    ),
    AnalystSpec(
        name="commercial_analyst",
        focus="commercial — discount and promotional activity assessment",
        tool_names=("get_discount_context", "get_activity_context", "get_sales_context"),
        system_prompt=_analyst_prompt(
            role="Commercial Analyst",
            domain_instructions=(
                "Assess whether pricing or promotional activity contributed to the sales move. "
                "Look at discount depth, discounted product rate, promotional activity rate, and promotional sales share. "
                "Assess whether any lift is likely driven by promotion, or whether a drop happened despite or because of promotion. "
                "IMPORTANT on margin: we have no cost or margin data. If significant promotion is present, "
                "flag margin dilution risk explicitly under data_gaps — do not invent margin figures."
            ),
        ),
    ),
    AnalystSpec(
        name="market_analyst",
        focus="market context — calendar, weather, and peer store comparison",
        tool_names=("get_calendar_weather_context", "get_peer_store_context", "get_sales_context"),
        system_prompt=_analyst_prompt(
            role="Market Analyst",
            domain_instructions=(
                "Assess external factors and whether the move is store-specific or broadly contextual. "
                "Look at calendar context (weekday, holiday), weather conditions, and how this store performed "
                "relative to peers. If the move is fleet-wide, that points to external factors. "
                "If it is isolated, that points to store-specific causes."
            ),
        ),
    ),
    AnalystSpec(
        name="research_analyst",
        focus="external research — web news search for broader market events on the date",
        tool_names=("search_news",),
        system_prompt=_analyst_prompt(
            role="Research Analyst",
            domain_instructions=(
                "Find relevant external news or events that may have influenced retail sales on this date. "
                "Search for news about retail conditions, economic events, or local events relevant to the store date. "
                "Report only what you find in search results — do not invent or infer beyond the evidence returned. "
                "This search is retrospective; findings are approximate and should be treated as LOW confidence."
            ),
        ),
    ),
)


COORDINATOR_SYSTEM_PROMPT = """You are the RCA coordinator analyst.

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


CRITIC_SYSTEM_PROMPT = """You are a skeptical RCA reviewer.

You review specialist memos before the coordinator synthesizes them.

Rules:
- Check whether claims are actually supported by the cited numbers.
- Flag correlation being presented as causation.
- Downgrade overconfident claims when evidence is thin.
- Keep the note concise and operational.
- Use plain ASCII markdown.

Return sections:
1. Claim Audit
2. Gaps
3. Calibration Note
"""


def plan_specialists(
    store_alias: str,
    dt: str,
    signal: dict[str, Any] | None = None,
) -> list[AnalystSpec]:
    """Planning seam — decides which specialists to dispatch.

    Returns all specialists. Later: filter by signal direction/magnitude.
    research_analyst is included but runs independently; its findings are
    additive and do not gate the core RCA.
    """
    return list(ANALYST_SPECS)


def _default_client_factory(settings: LLMSettings) -> ClientFactory:
    def factory(_: str) -> Any:
        return build_openai_compatible_client(settings)

    return factory


def _run_specialist(
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
        {
            "role": "system",
            "content": build_context_preamble(store_alias, dt) + "\n" + spec.system_prompt,
        },
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
        for tool_call in executed_tool_calls[-len(tool_calls):]:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["name"],
                    "content": json.dumps(tool_call["result"]),
                }
            )

    raise RuntimeError(f"{spec.name} exceeded the maximum tool rounds ({max_tool_rounds}).")


def _synthesize(
    store_alias: str,
    dt: str,
    analyst_results: list[AnalystRunResult],
    critic_note_markdown: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
) -> str:
    subject = f"{store_alias}:{dt}"
    client = client_factory("coordinator_analyst")
    memos = "\n\n".join(
        f"## {result.name}\nFocus: {result.focus}\n\n{result.memo_markdown}"
        for result in analyst_results
    )
    messages = [
        {
            "role": "system",
            "content": build_context_preamble(store_alias, dt) + "\n" + COORDINATOR_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Synthesize the specialist memos for store {store_alias} on {dt}.\n\n"
                f"Specialist memos:\n\n{memos}\n\n"
                f"Critic note:\n\n{critic_note_markdown}"
            ),
        },
    ]
    logger.log(
        actor_type="llm",
        actor_name="coordinator_analyst",
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
        actor_name="coordinator_analyst",
        action="completion_finished",
        subject=subject,
        source="llm",
        details={"content_preview": content[:200]},
    )
    return content


def _run_critic(
    store_alias: str,
    dt: str,
    analyst_results: list[AnalystRunResult],
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
) -> str:
    subject = f"{store_alias}:{dt}"
    client = client_factory("critic")
    memos = "\n\n".join(
        f"## {result.name}\nFocus: {result.focus}\n\n{result.memo_markdown}"
        for result in analyst_results
    )
    messages = [
        {
            "role": "system",
            "content": build_context_preamble(store_alias, dt) + "\n" + CRITIC_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Review the specialist memos for store {store_alias} on {dt}.\n\n"
                f"{memos}"
            ),
        },
    ]
    logger.log(
        actor_type="llm",
        actor_name="critic",
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
        actor_name="critic",
        action="completion_finished",
        subject=subject,
        source="llm",
        details={"content_preview": content[:200]},
    )
    return content


def run_coordinator(
    store_alias: str,
    dt: str,
    specialists: list[AnalystSpec] | None = None,
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
    output_dir: Path | None = None,
) -> CoordinatorResult:
    settings = settings or load_llm_settings()
    client_factory = client_factory or _default_client_factory(settings)
    run_name = f"{store_alias}_{dt}"
    logger = RunLogger(run_name=run_name)
    subject = f"{store_alias}:{dt}"

    if specialists is None:
        specialists = plan_specialists(store_alias, dt)

    logger.log(
        actor_type="workflow",
        actor_name="coordinator_pipeline",
        action="started",
        subject=subject,
        source="system",
        details={"analyst_count": len(specialists)},
    )

    def run_one(spec: AnalystSpec) -> AnalystRunResult:
        return _run_specialist(
            spec=spec,
            store_alias=store_alias,
            dt=dt,
            settings=settings,
            logger=logger,
            client_factory=client_factory,
        )

    with ThreadPoolExecutor(max_workers=len(specialists)) as executor:
        future_map = {spec.name: executor.submit(run_one, spec) for spec in specialists}
        results_by_name = {name: future.result() for name, future in future_map.items()}

    analyst_results = [results_by_name[spec.name] for spec in specialists]
    logger.log(
        actor_type="workflow",
        actor_name="coordinator_pipeline",
        action="analysts_completed",
        subject=subject,
        source="system",
        details={
            "analysts": [result.name for result in analyst_results],
            "tool_call_counts": {result.name: len(result.tool_calls) for result in analyst_results},
        },
    )

    critic_note = _run_critic(
        store_alias=store_alias,
        dt=dt,
        analyst_results=analyst_results,
        settings=settings,
        logger=logger,
        client_factory=client_factory,
    )
    logger.log(
        actor_type="workflow",
        actor_name="coordinator_pipeline",
        action="critic_completed",
        subject=subject,
        source="system",
        details={"critic_note_preview": critic_note[:200]},
    )

    coordinator_report = _synthesize(
        store_alias=store_alias,
        dt=dt,
        analyst_results=analyst_results,
        critic_note_markdown=critic_note,
        settings=settings,
        logger=logger,
        client_factory=client_factory,
    )
    logger.log(
        actor_type="workflow",
        actor_name="coordinator_pipeline",
        action="completed",
        subject=subject,
        source="system",
        details={
            "analyst_count": len(analyst_results),
            "output_dir": str(output_dir) if output_dir is not None else None,
        },
    )
    logger.write_to_db(LOG_DB_PATH)

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        specialist_dir = output_dir / "specialists"
        specialist_dir.mkdir(parents=True, exist_ok=True)
        for result in analyst_results:
            markdown_path = specialist_dir / f"{result.name}.md"
            html_path = specialist_dir / f"{result.name}.html"
            markdown_path.write_text(result.memo_markdown, encoding="utf-8")
            html_path.write_text(
                render_markdown_document(
                    result.memo_markdown,
                    title=f"{result.name} memo for {store_alias} on {dt}",
                ),
                encoding="utf-8",
            )
        critique_markdown_path = output_dir / "critique.md"
        critique_html_path = output_dir / "critique.html"
        critique_markdown_path.write_text(critic_note, encoding="utf-8")
        critique_html_path.write_text(
            render_markdown_document(
                critic_note,
                title=f"Critique for {store_alias} on {dt}",
            ),
            encoding="utf-8",
        )
        report_markdown_path = output_dir / "report.md"
        report_html_path = output_dir / "report.html"
        report_markdown_path.write_text(coordinator_report, encoding="utf-8")
        report_html_path.write_text(
            render_markdown_document(
                coordinator_report,
                title=f"RCA report for {store_alias} on {dt}",
            ),
            encoding="utf-8",
        )
        payload = {
            "store_alias": store_alias,
            "dt": dt,
            "critic_note_markdown": critic_note,
            "coordinator_report_markdown": coordinator_report,
            "analyst_results": [asdict(result) for result in analyst_results],
        }
        (output_dir / "coordinator_trace.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return CoordinatorResult(
        store_alias=store_alias,
        dt=dt,
        coordinator_report_markdown=coordinator_report,
        critic_note_markdown=critic_note,
        analyst_results=analyst_results,
    )
