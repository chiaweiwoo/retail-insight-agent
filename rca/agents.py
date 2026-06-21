from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from rca.config import AGENT_SKILLS_PATH, DEFAULT_LLM_MAX_TOOL_ROUNDS, SALES_FIELD_SEMANTICS, get_research_enabled
from rca.llm import LLMSettings, build_chat_completion_kwargs, build_openai_compatible_client, make_routed_settings
from rca.memory import get_memory_notes, write_memory
from rca.outcomes import record_completion
from rca.runlog import RunLogger
from rca.state import (
    CriticGap,
    CriticReview,
    DecisionBrief,
    EvidenceItem,
    InvestigationRound,
    MemoryInfluence,
    MonitoringPlan,
    RcaRunState,
)
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
    evidence_items: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PlannerDecision:
    selected_agents: list[str]
    rationale: str
    news_query: str
    objective: str = ""
    target_gaps: list[str] = field(default_factory=list)
    expected_evidence: list[str] = field(default_factory=list)


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
            "run_stat_analysis",
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


def _make_investigation_key(agent_name: str, target_gap_ids: list[str]) -> str:
    """Stable deduplication key so the repetition guard works across rounds."""
    if not target_gap_ids:
        return f"{agent_name}__initial"
    return f"{agent_name}__{'_'.join(sorted(target_gap_ids))}"


# ── Evidence conversion ───────────────────────────────────────────────────────


def agent_memo_to_evidence_items(result: AgentRunResult, state: RcaRunState) -> list[EvidenceItem]:
    """Convert an agent's tool calls and memo into typed EvidenceItem objects.

    One observation item per tool call (raw data retrieval), one inference item
    for the agent's written memo (interpretation of that data).
    """
    items: list[EvidenceItem] = []
    for tc in result.tool_calls:
        ev_id = state.next_evidence_id()
        raw_result = tc.get("result")
        payload = raw_result if isinstance(raw_result, dict) else {"raw": str(raw_result or "")}
        args: dict[str, Any] = tc.get("arguments") or {}
        city_hint = f" for city {args.get('city_id', '?')}" if args.get("city_id") is not None else ""
        items.append(
            EvidenceItem(
                id=ev_id,
                source=str(tc.get("name") or "unknown_tool"),
                tool_name=str(tc.get("name") or ""),
                agent_name=result.name,
                summary=f"{result.name} retrieved {tc.get('name')}{city_hint}",
                payload=payload,
                evidence_type="observation",
            )
        )
    if result.memo_markdown:
        ev_id = state.next_evidence_id()
        excerpt = result.memo_markdown[:500].strip()
        items.append(
            EvidenceItem(
                id=ev_id,
                source=result.name,
                agent_name=result.name,
                summary=f"{result.name}: {result.memo_markdown[:200].strip()}",
                payload={"memo_excerpt": excerpt},
                evidence_type="inference",
            )
        )
    return items


# ── Planner ───────────────────────────────────────────────────────────────────


def plan_investigation(
    *,
    city_id: int,
    dt: str,
    round_index: int = 1,
    prior_gaps: list[dict[str, Any]] | None = None,
    prior_evidence_summary: list[str] | None = None,
    signal_context: dict[str, Any] | None = None,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> PlannerDecision:
    research_enabled = get_research_enabled()
    signal = signal_context or get_signal_evidence(city_id, dt)
    sales = get_sales_context(city_id, dt, history_days=10)
    calendar_weather = get_calendar_weather_context(city_id, dt)
    memory = get_memory_context(city_id, limit=4)
    skill = _load_skill_text("planner.md")
    client = client_factory("planner")

    round_context = ""
    if round_index > 1 and prior_gaps:
        round_context = (
            f"\nThis is round {round_index}. Address these critic gaps:\n"
            + json.dumps(prior_gaps, ensure_ascii=False)
            + "\nRecent evidence gathered:\n"
            + "\n".join(f"- {s}" for s in (prior_evidence_summary or []))
            + "\nSelect agents that can fill these specific gaps.\n"
        )

    prompt = (
        "You are planning a city/date retail RCA investigation round. Return valid JSON only.\n"
        "Allowed agents: statistician, sales_agent, inventory_agent, pricing_agent, "
        "promotions_agent, calendar_weather_agent, news_agent.\n"
        + ("Round 1: always include statistician and sales_agent.\n" if round_index == 1 else "")
        + (
            "External web research is enabled.\n"
            if research_enabled
            else "External web research is disabled. Do not select news_agent.\n"
        )
        + "Return JSON: {selected_agents, rationale, news_query, objective, "
        "target_gaps (list of gap IDs from prior critic review), "
        "expected_evidence (list of strings)}\n"
        + f"{skill}\n"
        + round_context
    )
    user: dict[str, Any] = {
        "city_id": city_id,
        "dt": dt,
        "round_index": round_index,
        "signal": signal,
        "sales": sales,
        "calendar_weather": calendar_weather,
        "memory": memory,
    }
    if prior_gaps:
        user["prior_gaps"] = prior_gaps

    logger.log(
        actor_type="workflow",
        actor_name="planner",
        action="started",
        source="system",
        details={"round_index": round_index, "signal": signal},
    )
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
        selected_agents = [name for name in parsed.get("selected_agents", []) if name in SPEC_BY_NAME]
        if round_index == 1:
            if "statistician" not in selected_agents:
                selected_agents.insert(0, "statistician")
            if "sales_agent" not in selected_agents:
                selected_agents.insert(1, "sales_agent")
        if not research_enabled:
            selected_agents = [n for n in selected_agents if n != "news_agent"]
        decision = PlannerDecision(
            selected_agents=selected_agents,
            rationale=str(parsed.get("rationale") or ""),
            news_query=str(parsed.get("news_query") or f"city {city_id} retail news {dt}"),
            objective=str(parsed.get("objective") or f"Round {round_index} investigation."),
            target_gaps=list(parsed.get("target_gaps") or []),
            expected_evidence=list(parsed.get("expected_evidence") or []),
        )
    except Exception:
        # Fallback: use suggested agents from gaps, or default set for round 1
        if round_index > 1 and prior_gaps:
            suggested = []
            for g in prior_gaps:
                suggested.extend(g.get("suggested_agents") or [])
            fallback_agents = [n for n in suggested if n in SPEC_BY_NAME] or [
                "statistician",
                "sales_agent",
            ]
        else:
            fallback_agents = [
                "statistician",
                "sales_agent",
                "inventory_agent",
                "pricing_agent",
                "promotions_agent",
                "calendar_weather_agent",
            ]
        decision = PlannerDecision(
            selected_agents=fallback_agents,
            rationale="Fallback planner — JSON parsing failed.",
            news_query=f"city {city_id} retail news {dt}",
            objective=f"Round {round_index} fallback investigation.",
        )
    logger.log(
        actor_type="workflow",
        actor_name="planner",
        action="completed",
        source="llm",
        details={"round_index": round_index, "selected_agents": decision.selected_agents},
    )
    return decision


# ── Specialist agents ─────────────────────────────────────────────────────────


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
        logger.log(
            actor_type="agent",
            actor_name=spec.name,
            action="completed",
            source="system",
            details={"research_enabled": False},
        )
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
                + (
                    f" Use this external query if helpful: {news_query}."
                    if news_query and spec.name == "news_agent"
                    else ""
                )
            ),
        },
    ]
    logger.log(
        actor_type="agent", actor_name=spec.name, action="started", source="system", details={"focus": spec.focus}
    )
    executed_tool_calls: list[dict[str, Any]] = []
    tool_schemas = get_tool_schemas(spec.tool_names)

    for round_index in range(1, max_tool_rounds + 1):
        response = client.chat.completions.create(**build_chat_completion_kwargs(settings, messages, tool_schemas))
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


def _run_agents_parallel(
    *,
    agent_names: list[str],
    city_id: int,
    dt: str,
    news_query: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> list[AgentRunResult]:
    def _run_one(name: str) -> AgentRunResult:
        spec = SPEC_BY_NAME[name]
        return run_agent(
            spec=spec,
            city_id=city_id,
            dt=dt,
            settings=make_routed_settings(settings, name),
            logger=logger,
            client_factory=client_factory,
            run_id=run_id,
            news_query=news_query,
        )

    results: list[AgentRunResult] = []
    with ThreadPoolExecutor(max_workers=max(1, len(agent_names))) as executor:
        futures = {executor.submit(_run_one, name): name for name in agent_names}
        for future in as_completed(futures):
            results.append(future.result())

    order = {name: i for i, name in enumerate(agent_names)}
    results.sort(key=lambda r: order.get(r.name, 99))
    return results


# ── Structured critic ─────────────────────────────────────────────────────────

_GAP_TYPES = (
    "missing_internal_evidence|missing_external_context|weak_causal_link|"
    "baseline_conflict|scope_violation|format_violation|insufficient_business_action|unavailable_data"
)


def run_critic(
    *,
    city_id: int,
    dt: str,
    round_index: int,
    agent_results: list[AgentRunResult],
    evidence_ledger: list[dict[str, Any]],
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> CriticReview:
    client = client_factory("critic")
    skill = _load_skill_text("critic.md")
    memos = "\n\n".join(
        f"## {result.name}\nFocus: {result.focus}\n\n{result.memo_markdown}" for result in agent_results
    )

    system = (
        "You are the critic for a retail RCA investigation loop. Return valid JSON only.\n"
        "Schema: {\"continue_investigation\":<bool>,\"confidence_ceiling\":\"low|medium|high\","
        "\"gaps\":[{\"id\":\"gap_001\",\"description\":\"...\",\"severity\":\"low|medium|high\","
        f"\"gap_type\":\"{_GAP_TYPES}\","
        "\"suggested_agents\":[...],\"suggested_tools\":[...]}],"
        "\"recommended_agents\":[...],\"recommended_tools\":[...],\"stop_reason\":\"...\"}\n"
        "Set continue_investigation=false when: confidence_ceiling is high and gaps are minor, "
        "all remaining gaps are unavailable_data, or sufficient evidence exists.\n"
        "Do not identify product or store as root causes. "
        "Do not use dollar signs, revenue, profit, or margin.\n"
        + skill
    )
    logger.log(
        actor_type="agent",
        actor_name="critic",
        action="started",
        source="system",
        details={"round_index": round_index},
    )
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(
            settings,
            [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "city_id": city_id,
                            "dt": dt,
                            "round_index": round_index,
                            "evidence_count": len(evidence_ledger),
                            "recent_evidence": evidence_ledger[-5:],
                            "agent_memos": memos,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            tools=None,
        )
    )
    content = response.choices[0].message.content or "{}"
    _record_completion_response(
        run_id=run_id, city_id=city_id, dt=dt, node_name="critic", response=response, content=content
    )
    logger.log(
        actor_type="agent",
        actor_name="critic",
        action="completed",
        source="llm",
        details={"round_index": round_index},
    )
    try:
        parsed = _extract_json_object(content)
        gaps: list[CriticGap] = []
        for i, g in enumerate(parsed.get("gaps") or []):
            gaps.append(
                CriticGap(
                    id=str(g.get("id") or f"gap_{i + 1:03d}"),
                    description=str(g.get("description") or ""),
                    severity=g.get("severity") or "medium",
                    gap_type=g.get("gap_type") or "missing_internal_evidence",
                    suggested_agents=list(g.get("suggested_agents") or []),
                    suggested_tools=list(g.get("suggested_tools") or []),
                )
            )
        return CriticReview(
            round_index=round_index,
            continue_investigation=bool(parsed.get("continue_investigation", False)),
            confidence_ceiling=parsed.get("confidence_ceiling") or "low",
            gaps=gaps,
            recommended_agents=list(parsed.get("recommended_agents") or []),
            recommended_tools=list(parsed.get("recommended_tools") or []),
            stop_reason=str(parsed.get("stop_reason") or ""),
        )
    except Exception:
        return CriticReview(
            round_index=round_index,
            continue_investigation=False,
            confidence_ceiling="low",
            stop_reason="Critic JSON parsing failed — stopping conservatively.",
        )


# ── Bounded investigation loop ────────────────────────────────────────────────


def run_investigation_loop(
    *,
    city_id: int,
    dt: str,
    signal_evidence: dict[str, Any],
    memory_notes: list[dict[str, Any]],
    run_id: str,
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    max_rounds: int | None = None,
) -> RcaRunState:
    from rca.config import get_max_investigation_rounds, get_research_enabled as _research_enabled

    effective_max = max_rounds if max_rounds is not None else get_max_investigation_rounds()
    research_enabled = _research_enabled()

    state = RcaRunState(
        run_id=run_id,
        city_id=city_id,
        dt=dt,
        signal_label=str(signal_evidence.get("signal_label") or "neutral"),
    )
    used_keys: set[str] = set()

    for round_index in range(1, effective_max + 1):
        prior_gaps: list[dict[str, Any]] = []
        if state.critic_reviews:
            prior_gaps = [g.model_dump(mode="json") for g in state.critic_reviews[-1].gaps]
        prior_evidence_summary = [ev.summary for ev in state.evidence_ledger[-10:]]

        decision = plan_investigation(
            city_id=city_id,
            dt=dt,
            round_index=round_index,
            prior_gaps=prior_gaps,
            prior_evidence_summary=prior_evidence_summary,
            signal_context=signal_evidence,
            settings=make_routed_settings(settings, "planner"),
            logger=logger,
            client_factory=client_factory,
            run_id=run_id,
        )

        # Repetition guard: skip agent+gap combos already dispatched
        target_gap_ids = [g.get("id", "") for g in prior_gaps]
        filtered_agents: list[str] = []
        for agent_name in decision.selected_agents:
            key = _make_investigation_key(agent_name, target_gap_ids)
            if key not in used_keys:
                filtered_agents.append(agent_name)
                used_keys.add(key)

        # Gate news_agent: only after ≥1 internal round when critic identified an external gap
        if "news_agent" in filtered_agents:
            has_internal_evidence = any(ev.evidence_type != "external" for ev in state.evidence_ledger)
            has_external_gap = any(g.get("gap_type") == "missing_external_context" for g in prior_gaps)
            if not (research_enabled and has_internal_evidence and has_external_gap):
                filtered_agents = [a for a in filtered_agents if a != "news_agent"]

        if not filtered_agents:
            logger.log(
                actor_type="workflow",
                actor_name="investigation_loop",
                action="stopped",
                source="system",
                details={"round_index": round_index, "reason": "no_new_agent_gap_combos"},
            )
            break

        agent_results = _run_agents_parallel(
            agent_names=filtered_agents,
            city_id=city_id,
            dt=dt,
            news_query=decision.news_query,
            settings=settings,
            logger=logger,
            client_factory=client_factory,
            run_id=run_id,
        )

        # Convert agent output to evidence items
        new_evidence_ids: list[str] = []
        for result in agent_results:
            items = agent_memo_to_evidence_items(result, state)
            state.evidence_ledger.extend(items)
            new_evidence_ids.extend(ev.id for ev in items)
            result.evidence_items = [ev.model_dump(mode="json") for ev in items]

        critic_review = run_critic(
            city_id=city_id,
            dt=dt,
            round_index=round_index,
            agent_results=agent_results,
            evidence_ledger=[ev.model_dump(mode="json") for ev in state.evidence_ledger],
            settings=make_routed_settings(settings, "critic"),
            logger=logger,
            client_factory=client_factory,
            run_id=run_id,
        )
        state.critic_reviews.append(critic_review)

        round_ = InvestigationRound(
            round_index=round_index,
            objective=decision.objective,
            selected_agents=decision.selected_agents,
            completed_agents=[r.name for r in agent_results],
            new_evidence_ids=new_evidence_ids,
            critic_review=critic_review,
        )
        state.investigation_rounds.append(round_)

        # Stop conditions
        if not critic_review.continue_investigation:
            break

        # All identified gaps are unavailable_data → nothing actionable remains
        if critic_review.gaps:
            actionable_gaps = [g for g in critic_review.gaps if g.gap_type != "unavailable_data"]
            if not actionable_gaps:
                logger.log(
                    actor_type="workflow",
                    actor_name="investigation_loop",
                    action="stopped",
                    source="system",
                    details={"round_index": round_index, "reason": "only_unavailable_data_gaps"},
                )
                break

    state.memory_context = MemoryInfluence(
        used=bool(memory_notes),
        memory_ids=[],
        effect="Memory notes provided to planner." if memory_notes else "No relevant memory found.",
    )
    return state


# ── Decision brief synthesis ──────────────────────────────────────────────────


def _brief_to_markdown(brief: DecisionBrief, signal_label: str) -> str:
    lines = [
        "# Decision Card",
        f"- headline: {brief.headline}",
        f"- confidence: {brief.confidence}",
        f"- signal: {signal_label}",
        "",
        "## RCA",
        brief.situation,
        "",
        brief.most_likely_explanation,
        "",
        "## Business Impact",
        brief.business_impact,
        "",
        "## Evidence Summary",
    ]
    for ev in brief.evidence_summary:
        lines.append(f"- {ev}")
    lines += [
        "",
        "## Prediction",
    ]
    mp = brief.monitoring_plan
    if mp.metrics_to_watch:
        lines.append(f"Watch: {', '.join(mp.metrics_to_watch)}")
    if mp.review_horizon:
        lines.append(f"Review horizon: {mp.review_horizon}")
    if mp.escalation_trigger:
        lines.append(f"Escalation trigger: {mp.escalation_trigger}")
    lines += [
        "",
        "## Prescription",
        brief.recommended_action,
    ]
    if brief.alternatives:
        lines.append("Alternatives:")
        for alt in brief.alternatives:
            lines.append(f"- {alt}")
    if brief.unknowns:
        lines += ["", "## Unknowns"]
        for u in brief.unknowns:
            lines.append(f"- {u}")
    if brief.caveats:
        lines += ["", "## Caveats"]
        for c in brief.caveats:
            lines.append(f"- {c}")
    return "\n".join(lines)


def run_decision_brief(
    *,
    city_id: int,
    dt: str,
    signal_evidence: dict[str, Any],
    investigation_rounds: list[dict[str, Any]],
    evidence_ledger: list[dict[str, Any]],
    critic_reviews: list[dict[str, Any]],
    memory_notes: list[dict[str, Any]],
    settings: LLMSettings,
    logger: RunLogger,
    client_factory: ClientFactory,
    run_id: str,
) -> tuple[DecisionBrief, str]:
    skill = _load_skill_text("coordinator.md")
    signal_label = str(signal_evidence.get("signal_label") or "neutral")
    client = client_factory("coordinator")

    ev_summaries = [ev.get("summary", "") for ev in evidence_ledger[-10:]]
    last_critic = critic_reviews[-1] if critic_reviews else {}

    system = (
        "You are the final synthesis coordinator for a retail RCA. Return valid JSON only.\n"
        f"{SALES_FIELD_SEMANTICS}\n"
        'Schema: {"headline":"<one line>","confidence":"low|medium|high",'
        '"situation":"<2-3 sentences>","business_impact":"<1-2 sentences>",'
        '"most_likely_explanation":"<2-3 sentences>","evidence_summary":["<bullet>",...],'
        '"recommended_action":"<1-2 sentences>","alternatives":["<alt>",...],'
        '"owner_function":"<function>","urgency":"low|medium|high","expected_benefit":"<1 sentence>",'
        '"monitoring_plan":{"metrics_to_watch":[...],"review_horizon":"...","escalation_trigger":"..."},'
        '"unknowns":["<unknown>",...],"caveats":["<caveat>",...]}\n'
        "Rules:\n"
        "- Do not mention product or store as root causes.\n"
        "- Do not use dollar signs, revenue, profit, or margin without explicit data.\n"
        "- Use 'insufficient evidence' when data is absent. Do not force a cause.\n"
        "- External evidence is supportive only; internal facts are primary.\n"
        + skill
    )
    user_context: dict[str, Any] = {
        "city_id": city_id,
        "dt": dt,
        "signal": signal_evidence,
        "investigation_rounds": len(investigation_rounds),
        "evidence_count": len(evidence_ledger),
        "evidence_summaries": ev_summaries,
        "last_critic_review": last_critic,
        "recent_memory": memory_notes,
    }

    logger.log(
        actor_type="agent",
        actor_name="coordinator",
        action="started",
        source="system",
        details={"round_count": len(investigation_rounds)},
    )
    response = client.chat.completions.create(
        **build_chat_completion_kwargs(
            settings,
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user_context, ensure_ascii=False)},
            ],
            tools=None,
        )
    )
    content = response.choices[0].message.content or "{}"
    _record_completion_response(
        run_id=run_id, city_id=city_id, dt=dt, node_name="coordinator", response=response, content=content
    )
    logger.log(actor_type="agent", actor_name="coordinator", action="completed", source="llm", details={})

    try:
        parsed = _extract_json_object(content)
        monitoring_raw = parsed.get("monitoring_plan") or {}
        monitoring = MonitoringPlan(
            metrics_to_watch=list(monitoring_raw.get("metrics_to_watch") or []),
            review_horizon=str(monitoring_raw.get("review_horizon") or ""),
            escalation_trigger=str(monitoring_raw.get("escalation_trigger") or ""),
        ) if isinstance(monitoring_raw, dict) else MonitoringPlan()
        brief = DecisionBrief(
            headline=str(parsed.get("headline") or ""),
            confidence=parsed.get("confidence") or "low",
            situation=str(parsed.get("situation") or ""),
            business_impact=str(parsed.get("business_impact") or ""),
            most_likely_explanation=str(parsed.get("most_likely_explanation") or ""),
            evidence_summary=list(parsed.get("evidence_summary") or []),
            recommended_action=str(parsed.get("recommended_action") or ""),
            alternatives=list(parsed.get("alternatives") or []),
            owner_function=str(parsed.get("owner_function") or ""),
            urgency=parsed.get("urgency") or "medium",
            expected_benefit=str(parsed.get("expected_benefit") or ""),
            monitoring_plan=monitoring,
            unknowns=list(parsed.get("unknowns") or []),
            caveats=list(parsed.get("caveats") or []),
        )
    except Exception:
        brief = DecisionBrief(
            headline="Decision brief parsing failed — insufficient evidence.",
            confidence="low",
            situation="Unable to parse structured decision from coordinator output.",
            business_impact="Unknown.",
            most_likely_explanation="Insufficient evidence to determine root cause.",
            recommended_action="Re-run investigation with more data.",
            owner_function="Analytics",
            urgency="low",
            expected_benefit="Clearer signal after re-run.",
        )

    markdown = _brief_to_markdown(brief, signal_label)
    return brief, markdown


# ── Memory distiller ──────────────────────────────────────────────────────────


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
) -> tuple[str, dict[str, Any]]:
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

    lessons: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            lessons.append(stripped[2:].strip())

    memory_json: dict[str, Any] = {"lessons": lessons, "version": 1}
    write_memory(
        city_id=city_id,
        dt=dt,
        run_id=run_id,
        memory_type="lesson",
        topic="rca_lesson",
        content=content,
        signal_label=signal_label,
        memory_json=memory_json,
        influence_score=0.5,
    )
    logger.log(actor_type="agent", actor_name="memory_distiller", action="completed", source="llm", details={})
    return content, memory_json


# ── Markdown extraction (kept for decision card column rendering) ──────────────


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
