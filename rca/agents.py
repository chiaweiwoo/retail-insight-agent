from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable

from rca.config import AGENT_SKILLS_PATH, DEFAULT_LLM_MAX_TOOL_ROUNDS, SALES_FIELD_SEMANTICS, get_research_enabled
from rca.llm import LLMSettings, build_chat_completion_kwargs, build_openai_compatible_client
from rca.memory import get_memory_notes, write_memory
from rca.outcomes import record_completion
from rca.runlog import RunLogger
from rca.tools import (
    execute_tool,
    get_calendar_weather_context,
    get_memory_context,
    get_sales_context,
    get_signal_evidence,
    get_tool_schemas,
)


ClientFactory = Callable[[str], Any]


@dataclass(frozen=True)
class AgentSpec:
    name: str
    focus: str
    tool_names: tuple[str, ...]
    skill_file: str


@dataclass
class AgentRunResult:
    name: str
    focus: str
    memo_markdown: str
    tool_calls: list[dict[str, Any]]


@dataclass
class PlannerDecision:
    selected_agents: list[str]
    rationale: str
    news_query: str


AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec(
        name="statistician",
        focus="validate the signal with runtime baselines, intraday shape, and descriptive statistics",
        tool_names=(
            "get_signal_evidence",
            "get_sales_context",
            "compare_recent_baseline",
            "compare_same_weekday_baseline",
            "detect_intraday_shift",
            "get_intraday_profile",
        ),
        skill_file="statistician.md",
    ),
    AgentSpec(
        name="sales_agent",
        focus="explain sales movement versus expected sales and recent history",
        tool_names=("get_signal_evidence", "get_sales_context"),
        skill_file="sales.md",
    ),
    AgentSpec(
        name="inventory_agent",
        focus="assess whether stockout or availability pressure likely contributed to the move",
        tool_names=("get_inventory_context", "get_intraday_profile", "compare_recent_baseline"),
        skill_file="inventory.md",
    ),
    AgentSpec(
        name="pricing_agent",
        focus="assess discount depth and pricing pressure",
        tool_names=("get_pricing_context", "get_signal_evidence"),
        skill_file="pricing.md",
    ),
    AgentSpec(
        name="promotions_agent",
        focus="assess the unlabeled activity indicator and possible promotion contribution",
        tool_names=("get_promotions_context", "get_signal_evidence"),
        skill_file="promotions.md",
    ),
    AgentSpec(
        name="calendar_weather_agent",
        focus="assess calendar, inferred holiday, and weather context",
        tool_names=("get_calendar_weather_context", "get_signal_evidence"),
        skill_file="calendar_weather.md",
    ),
    AgentSpec(
        name="news_agent",
        focus="search for external events and news that may explain the city/date movement",
        tool_names=("search_external_events",),
        skill_file="news.md",
    ),
)

SPEC_BY_NAME = {spec.name: spec for spec in AGENT_SPECS}


def _load_skill_text(skill_file: str) -> str:
    path = AGENT_SKILLS_PATH / skill_file
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _record_completion_response(
    *,
    run_id: str,
    city_id: int,
    dt: str,
    node_name: str,
    response: Any,
    content: str,
    tool_calls_json: list[dict[str, Any]] | None = None,
) -> None:
    usage = getattr(response, "usage", None)
    record_completion(
        run_id=run_id,
        city_id=city_id,
        dt=dt,
        node_name=node_name,
        model=getattr(response, "model", "unknown"),
        content=content,
        prompt_tokens=getattr(usage, "prompt_tokens", None),
        completion_tokens=getattr(usage, "completion_tokens", None),
        tool_calls_json=tool_calls_json,
    )


def _default_client_factory(settings: LLMSettings) -> ClientFactory:
    def factory(_: str) -> Any:
        return build_openai_compatible_client(settings)

    return factory


def plan_investigation(
    *,
    city_id: int,
    dt: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> PlannerDecision:
    research_enabled = get_research_enabled()
    signal = get_signal_evidence(city_id, dt)
    sales = get_sales_context(city_id, dt, history_days=10)
    calendar_weather = get_calendar_weather_context(city_id, dt)
    memory = get_memory_context(city_id, limit=4)
    skill = _load_skill_text("planner.md")
    client = client_factory("planner")

    prompt = (
        "You are planning a city/date retail RCA. Return valid JSON only.\n"
        "Allowed agents: statistician, sales_agent, inventory_agent, pricing_agent, "
        "promotions_agent, calendar_weather_agent, news_agent.\n"
        "Always include statistician and sales_agent.\n"
        + ("External web research is enabled.\n" if research_enabled else "External web research is disabled, so do not select news_agent.\n")
        + f"{skill}\n"
    )
    user = {
        "signal": signal,
        "sales": sales,
        "calendar_weather": calendar_weather,
        "memory": memory,
    }
    logger.log(actor_type="workflow", actor_name="planner", action="started", source="system", details={"signal": signal})
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(
            settings,
            [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
            ],
            tools=None,
        )
    )
    content = response.choices[0].message.content or "{}"
    _record_completion_response(
        run_id=run_id,
        city_id=city_id,
        dt=dt,
        node_name="planner",
        response=response,
        content=content,
    )
    try:
        parsed = _extract_json_object(content)
        selected_agents = [
            name
            for name in parsed.get("selected_agents", [])
            if name in SPEC_BY_NAME
        ]
        if "statistician" not in selected_agents:
            selected_agents.insert(0, "statistician")
        if "sales_agent" not in selected_agents:
            selected_agents.insert(1, "sales_agent")
        if research_enabled and "news_agent" not in selected_agents:
            selected_agents.append("news_agent")
        if not research_enabled:
            selected_agents = [name for name in selected_agents if name != "news_agent"]
        decision = PlannerDecision(
            selected_agents=selected_agents,
            rationale=str(parsed.get("rationale") or ""),
            news_query=str(parsed.get("news_query") or f"city {city_id} retail news {dt}"),
        )
    except Exception:
        decision = PlannerDecision(
            selected_agents=[
                "statistician",
                "sales_agent",
                "inventory_agent",
                "pricing_agent",
                "promotions_agent",
                "calendar_weather_agent",
            ],
            rationale="Fallback planner path used because structured parsing failed.",
            news_query=f"city {city_id} retail news {dt}",
        )
        if research_enabled:
            decision.selected_agents.append("news_agent")
    logger.log(
        actor_type="workflow",
        actor_name="planner",
        action="completed",
        source="llm",
        details={"selected_agents": decision.selected_agents, "news_query": decision.news_query},
    )
    return decision


def run_agent(
    *,
    spec: AgentSpec,
    city_id: int,
    dt: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
    news_query: str = "",
    max_tool_rounds: int = DEFAULT_LLM_MAX_TOOL_ROUNDS,
) -> AgentRunResult:
    if spec.name == "news_agent" and not get_research_enabled():
        content = (
            "## Why It Matters\n"
            "External factors may still matter for a city-wide move.\n\n"
            "## Evidence\n"
            "- Web research is disabled by configuration (`RCA_RESEARCH_ENABLED=false`).\n\n"
            "## Interpretation\n"
            "- No external news evidence was gathered in this run.\n\n"
            "## Caveats\n"
            "- Any external explanation remains untested until research is enabled.\n"
        )
        logger.log(actor_type="agent", actor_name=spec.name, action="completed", source="system", details={"research_enabled": False})
        return AgentRunResult(name=spec.name, focus=spec.focus, memo_markdown=content, tool_calls=[])

    client = client_factory(spec.name)
    system_prompt = (
        f"You are a retail RCA agent focused on {spec.focus}.\n"
        f"{SALES_FIELD_SEMANTICS}\n"
        "Use plain ASCII markdown. Distinguish observation from inference.\n"
        "Return sections:\n"
        "## Why It Matters\n## Evidence\n## Interpretation\n## Caveats\n"
    )
    skill = _load_skill_text(spec.skill_file)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt + "\n" + skill},
        {
            "role": "user",
            "content": (
                f"Analyze city {city_id} on {dt}. Focus: {spec.focus}."
                + (f" Use this external query if helpful: {news_query}." if news_query and spec.name == "news_agent" else "")
            ),
        },
    ]
    logger.log(actor_type="agent", actor_name=spec.name, action="started", source="system", details={"focus": spec.focus})
    executed_tool_calls: list[dict[str, Any]] = []
    tool_schemas = get_tool_schemas(spec.tool_names)

    for round_index in range(1, max_tool_rounds + 1):
        response = client.chat.completions.create(
            **build_chat_completion_kwargs(settings, messages, tool_schemas)
        )
        message = response.choices[0].message
        tool_calls = getattr(message, "tool_calls", None)

        if not tool_calls:
            content = message.content or ""
            _record_completion_response(
                run_id=run_id,
                city_id=city_id,
                dt=dt,
                node_name=spec.name,
                response=response,
                content=content,
                tool_calls_json=executed_tool_calls,
            )
            logger.log(
                actor_type="agent",
                actor_name=spec.name,
                action="completed",
                source="llm",
                details={"tool_call_count": len(executed_tool_calls)},
            )
            return AgentRunResult(
                name=spec.name,
                focus=spec.focus,
                memo_markdown=content,
                tool_calls=executed_tool_calls,
            )

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": getattr(message, "content", None) or "",
            "tool_calls": [],
        }
        tool_call_logs: list[dict[str, Any]] = []
        for tool_call in tool_calls:
            arguments = json.loads(tool_call.function.arguments or "{}")
            if spec.name == "news_agent":
                arguments.setdefault("city_id", city_id)
                arguments.setdefault("dt", dt)
                arguments.setdefault("query", news_query or f"city {city_id} retail news {dt}")
            result = execute_tool(tool_call.function.name, arguments)
            log_row = {
                "id": tool_call.id,
                "name": tool_call.function.name,
                "arguments": arguments,
                "result": result,
            }
            executed_tool_calls.append(log_row)
            tool_call_logs.append(log_row)
            logger.log(
                actor_type="tool",
                actor_name=tool_call.function.name,
                action="completed",
                source=spec.name,
                details={"arguments": arguments},
            )
            assistant_message["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": json.dumps(arguments, ensure_ascii=False),
                    },
                }
            )
        _record_completion_response(
            run_id=run_id,
            city_id=city_id,
            dt=dt,
            node_name=spec.name,
            response=response,
            content=getattr(message, "content", None) or "",
            tool_calls_json=tool_call_logs,
        )
        messages.append(assistant_message)
        for tool_call in tool_call_logs:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_call["name"],
                    "content": json.dumps(tool_call["result"], ensure_ascii=False),
                }
            )

    raise RuntimeError(f"{spec.name} exceeded the maximum tool rounds ({max_tool_rounds}).")


def run_critic(
    *,
    city_id: int,
    dt: str,
    agent_results: list[AgentRunResult],
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> str:
    client = client_factory("critic")
    skill = _load_skill_text("critic.md")
    memos = "\n\n".join(
        f"## {result.name}\nFocus: {result.focus}\n\n{result.memo_markdown}"
        for result in agent_results
    )
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(
            settings,
            [
                {
                    "role": "system",
                    "content": (
                        "You are the critic for a retail RCA workflow.\n"
                        "Return sections:\n## Claim Audit\n## Gaps\n## Calibration\n## Follow Up\n"
                        + skill
                    ),
                },
                {
                    "role": "user",
                    "content": f"Review the following agent memos for city {city_id} on {dt}.\n\n{memos}",
                },
            ],
            tools=None,
        )
    )
    content = response.choices[0].message.content or ""
    _record_completion_response(
        run_id=run_id,
        city_id=city_id,
        dt=dt,
        node_name="critic",
        response=response,
        content=content,
    )
    logger.log(actor_type="agent", actor_name="critic", action="completed", source="llm", details={})
    return content


def run_coordinator(
    *,
    city_id: int,
    dt: str,
    signal_evidence: dict[str, Any],
    planner_decision: PlannerDecision,
    agent_results: list[AgentRunResult],
    critic_note: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> str:
    client = client_factory("coordinator")
    skill = _load_skill_text("coordinator.md")
    memory = get_memory_notes(city_id, limit=5)
    memos = "\n\n".join(
        f"## {result.name}\nFocus: {result.focus}\n\n{result.memo_markdown}"
        for result in agent_results
    )
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(
            settings,
            [
                {
                    "role": "system",
                    "content": (
                        "You are the coordinator for a retail RCA system.\n"
                        "Return exactly these sections in markdown:\n"
                        "# Decision Card\n"
                        "- headline: <one line>\n"
                        "- confidence: <high | medium | low>\n"
                        "- signal: <drop | lift | neutral | insufficient_history>\n"
                        "## RCA\n## Internal Factors\n## External Factors\n## Prediction\n## Prescription\n## Caveats\n"
                        + skill
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "city_id": city_id,
                            "dt": dt,
                            "signal_evidence": signal_evidence,
                            "planner_decision": asdict(planner_decision),
                            "recent_memory": memory,
                            "critic_note": critic_note,
                            "agent_memos": [asdict(item) for item in agent_results],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            tools=None,
        )
    )
    content = response.choices[0].message.content or ""
    _record_completion_response(
        run_id=run_id,
        city_id=city_id,
        dt=dt,
        node_name="coordinator",
        response=response,
        content=content,
    )
    logger.log(actor_type="agent", actor_name="coordinator", action="completed", source="llm", details={})
    return content


def run_memory_distiller(
    *,
    city_id: int,
    dt: str,
    signal_label: str,
    final_report: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> str:
    client = client_factory("memory_distiller")
    skill = _load_skill_text("memory_distiller.md")
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(
            settings,
            [
                {
                    "role": "system",
                    "content": (
                        "Write short reusable city lessons from one RCA run.\n"
                        "Return markdown with section ## Lessons and 3-5 bullets.\n"
                        + skill
                    ),
                },
                {"role": "user", "content": final_report},
            ],
            tools=None,
        )
    )
    content = response.choices[0].message.content or ""
    _record_completion_response(
        run_id=run_id,
        city_id=city_id,
        dt=dt,
        node_name="memory_distiller",
        response=response,
        content=content,
    )
    write_memory(
        city_id=city_id,
        dt=dt,
        run_id=run_id,
        memory_type="lesson",
        topic="rca_lesson",
        content=content,
        signal_label=signal_label,
    )
    logger.log(actor_type="agent", actor_name="memory_distiller", action="completed", source="llm", details={})
    return content


def extract_outcome_fields(markdown: str) -> dict[str, str]:
    def bullet(name: str) -> str:
        match = re.search(rf"^- {re.escape(name)}:\s*(.+)$", markdown, re.MULTILINE)
        return match.group(1).strip() if match else ""

    def section(title: str) -> str:
        match = re.search(
            rf"^## {re.escape(title)}\s*(.*?)(?=^## |\Z)",
            markdown,
            re.MULTILINE | re.DOTALL,
        )
        return match.group(1).strip() if match else ""

    return {
        "headline": bullet("headline"),
        "confidence": bullet("confidence") or "medium",
        "signal": bullet("signal"),
        "decision_card": markdown.split("## RCA", 1)[0].strip(),
        "rca": section("RCA"),
        "prediction": section("Prediction"),
        "prescription": section("Prescription"),
    }
