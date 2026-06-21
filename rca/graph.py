"""LangGraph orchestration for the v2 city/date RCA workflow."""
from __future__ import annotations

import operator
from dataclasses import asdict
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from typing_extensions import TypedDict

from rca.agents import (
    AGENT_SPECS,
    AgentRunResult,
    PlannerDecision,
    extract_outcome_fields,
    plan_investigation,
    run_agent,
    run_coordinator,
    run_critic,
    run_memory_distiller,
)
from rca.llm import ClientFactory, LLMSettings, build_openai_compatible_client, load_llm_settings, make_routed_settings
from rca.outcomes import OutcomeRecord, record_outcome
from rca.runlog import RunLogger
from rca.signals import get_signal_row


class RcaState(TypedDict):
    city_id: int
    dt: str
    run_id: str
    signal_evidence: dict[str, Any]
    planner_decision: dict[str, Any]
    agent_results: Annotated[list[dict[str, Any]], operator.add]
    critic_note: str
    final_report: str
    memory_note: str


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    return config.get("configurable") or {}


def _restore_agent_results(state: RcaState) -> list[AgentRunResult]:
    return [
        AgentRunResult(
            name=item["name"],
            focus=item["focus"],
            memo_markdown=item["memo_markdown"],
            tool_calls=item["tool_calls"],
        )
        for item in state["agent_results"]
    ]


def plan_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]
    signal_evidence = get_signal_row(state["city_id"], state["dt"])
    decision = plan_investigation(
        city_id=state["city_id"],
        dt=state["dt"],
        settings=make_routed_settings(settings, "planner"),
        logger=logger,
        client_factory=client_factory,
        run_id=state["run_id"],
    )
    return {"signal_evidence": signal_evidence, "planner_decision": asdict(decision)}


def route_agents(state: RcaState) -> list[Send]:
    planner_decision = PlannerDecision(**state["planner_decision"])
    return [
        Send(
            "run_agent",
            {
                "spec_name": name,
                "news_query": planner_decision.news_query,
                "city_id": state["city_id"],
                "dt": state["dt"],
                "run_id": state["run_id"],
            },
        )
        for name in planner_decision.selected_agents
    ]


def run_agent_node(state: dict[str, Any], config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]
    spec = next(spec for spec in AGENT_SPECS if spec.name == state["spec_name"])
    result = run_agent(
        spec=spec,
        city_id=state["city_id"],
        dt=state["dt"],
        settings=make_routed_settings(settings, spec.name),
        logger=logger,
        client_factory=client_factory,
        run_id=state["run_id"],
        news_query=state.get("news_query", ""),
    )
    return {"agent_results": [asdict(result)]}


def critic_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]
    note = run_critic(
        city_id=state["city_id"],
        dt=state["dt"],
        agent_results=_restore_agent_results(state),
        settings=make_routed_settings(settings, "critic"),
        logger=logger,
        client_factory=client_factory,
        run_id=state["run_id"],
    )
    return {"critic_note": note}


def coordinator_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]
    final_report = run_coordinator(
        city_id=state["city_id"],
        dt=state["dt"],
        signal_evidence=state["signal_evidence"],
        planner_decision=PlannerDecision(**state["planner_decision"]),
        agent_results=_restore_agent_results(state),
        critic_note=state["critic_note"],
        settings=make_routed_settings(settings, "coordinator"),
        logger=logger,
        client_factory=client_factory,
        run_id=state["run_id"],
    )
    return {"final_report": final_report}


def memory_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]
    memory_note = run_memory_distiller(
        city_id=state["city_id"],
        dt=state["dt"],
        signal_label=str(state["signal_evidence"].get("signal_label") or ""),
        final_report=state["final_report"],
        settings=make_routed_settings(settings, "memory_distiller"),
        logger=logger,
        client_factory=client_factory,
        run_id=state["run_id"],
    )
    return {"memory_note": memory_note}


def record_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    logger: RunLogger = _cfg(config)["logger"]
    outcome_fields = extract_outcome_fields(state["final_report"])
    record_outcome(
        OutcomeRecord(
            run_id=state["run_id"],
            city_id=state["city_id"],
            dt=state["dt"],
            signal_label=str(state["signal_evidence"].get("signal_label") or ""),
            confidence=outcome_fields["confidence"],
            headline=outcome_fields["headline"],
            decision_card_markdown=outcome_fields["decision_card"],
            report_markdown=outcome_fields["rca"],
            prediction_markdown=outcome_fields["prediction"],
            prescription_markdown=outcome_fields["prescription"],
            status="complete",
            round_count=1,
        )
    )
    logger.log(actor_type="workflow", actor_name="rca_run", action="completed", source="system", details={})
    logger.flush_to_supabase()
    return {}


def build_rca_graph() -> Any:
    builder: StateGraph = StateGraph(RcaState)
    builder.add_node("plan", plan_node)
    builder.add_node("run_agent", run_agent_node)
    builder.add_node("critic", critic_node)
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("memory", memory_node)
    builder.add_node("record", record_node)

    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", route_agents, ["run_agent"])
    builder.add_edge("run_agent", "critic")
    builder.add_edge("critic", "coordinator")
    builder.add_edge("coordinator", "memory")
    builder.add_edge("memory", "record")
    builder.add_edge("record", END)
    return builder.compile()


def run_rca_graph(
    city_id: int,
    dt: str,
    *,
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    settings = settings or load_llm_settings()
    base_factory: ClientFactory = client_factory or (lambda _: build_openai_compatible_client(settings))
    run_id = f"{city_id}_{dt}"
    logger = RunLogger(run_id=run_id, city_id=city_id, dt=dt)
    logger.log(actor_type="workflow", actor_name="rca_run", action="started", source="system", details={})

    graph = build_rca_graph()
    final_state: RcaState = graph.invoke(
        {
            "city_id": city_id,
            "dt": dt,
            "run_id": run_id,
            "signal_evidence": {},
            "planner_decision": {},
            "agent_results": [],
            "critic_note": "",
            "final_report": "",
            "memory_note": "",
        },
        config={"configurable": {"settings": settings, "client_factory": base_factory, "logger": logger}},
    )
    return {
        "run_id": run_id,
        "signal_evidence": final_state["signal_evidence"],
        "planner_decision": final_state["planner_decision"],
        "agent_results": _restore_agent_results(final_state),
        "critic_note": final_state["critic_note"],
        "final_report": final_state["final_report"],
        "memory_note": final_state["memory_note"],
    }
