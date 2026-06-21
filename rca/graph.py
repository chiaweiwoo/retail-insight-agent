"""LangGraph orchestration for the v2 city/date RCA workflow.

Graph: plan -> investigation_loop -> decision -> evaluation -> memory -> record
The investigation_loop node contains the bounded multi-round loop internally.
"""
from __future__ import annotations

from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from rca.agents import (
    extract_outcome_fields,
    run_decision_brief,
    run_investigation_loop,
    run_memory_distiller,
)
from rca.audits import run_evaluation
from rca.llm import ClientFactory, LLMSettings, build_openai_compatible_client, load_llm_settings, make_routed_settings
from rca.memory import get_memory_notes
from rca.outcomes import OutcomeRecord, record_outcome
from rca.runlog import RunLogger
from rca.signals import get_signal_row


class RcaState(TypedDict):
    city_id: int
    dt: str
    run_id: str
    signal_evidence: dict[str, Any]
    # From investigation_loop
    investigation_rounds: list[dict[str, Any]]
    evidence_ledger: list[dict[str, Any]]
    critic_reviews: list[dict[str, Any]]
    round_count: int
    memory_context: dict[str, Any]
    # From decision
    decision_brief: dict[str, Any]
    decision_card_markdown: str
    report_markdown: str
    prediction_markdown: str
    prescription_markdown: str
    # From evaluation
    evaluation: dict[str, Any]
    # From memory
    memory_note: str


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    return config.get("configurable") or {}


def investigation_loop_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]

    signal_evidence = get_signal_row(state["city_id"], state["dt"])
    memory_notes = get_memory_notes(state["city_id"], limit=5)

    run_state = run_investigation_loop(
        city_id=state["city_id"],
        dt=state["dt"],
        signal_evidence=signal_evidence,
        memory_notes=memory_notes,
        run_id=state["run_id"],
        settings=settings,
        logger=logger,
        client_factory=client_factory,
    )
    return {
        "signal_evidence": signal_evidence,
        "investigation_rounds": [r.model_dump(mode="json") for r in run_state.investigation_rounds],
        "evidence_ledger": [ev.model_dump(mode="json") for ev in run_state.evidence_ledger],
        "critic_reviews": [cr.model_dump(mode="json") for cr in run_state.critic_reviews],
        "round_count": len(run_state.investigation_rounds),
        "memory_context": run_state.memory_context.model_dump(mode="json"),
    }


def decision_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]

    memory_notes = get_memory_notes(state["city_id"], limit=5)
    brief, markdown = run_decision_brief(
        city_id=state["city_id"],
        dt=state["dt"],
        signal_evidence=state["signal_evidence"],
        investigation_rounds=state["investigation_rounds"],
        evidence_ledger=state["evidence_ledger"],
        critic_reviews=state["critic_reviews"],
        memory_notes=memory_notes,
        settings=make_routed_settings(settings, "coordinator"),
        logger=logger,
        client_factory=client_factory,
        run_id=state["run_id"],
    )
    outcome_fields = extract_outcome_fields(markdown)
    return {
        "decision_brief": brief.model_dump(mode="json"),
        "decision_card_markdown": outcome_fields.get("decision_card", markdown),
        "report_markdown": outcome_fields.get("rca", ""),
        "prediction_markdown": outcome_fields.get("prediction", ""),
        "prescription_markdown": outcome_fields.get("prescription", ""),
    }


def evaluation_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    evaluation = run_evaluation(
        decision_brief=state["decision_brief"],
        evidence_ledger=state["evidence_ledger"],
    )
    return {"evaluation": evaluation.model_dump(mode="json")}


def memory_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    cfg = _cfg(config)
    settings: LLMSettings = cfg["settings"]
    logger: RunLogger = cfg["logger"]
    client_factory: ClientFactory = cfg["client_factory"]
    signal_label = str(state["signal_evidence"].get("signal_label") or "")
    memory_note, _ = run_memory_distiller(
        city_id=state["city_id"],
        dt=state["dt"],
        signal_label=signal_label,
        final_report=state["decision_card_markdown"],
        settings=make_routed_settings(settings, "memory_distiller"),
        logger=logger,
        client_factory=client_factory,
        run_id=state["run_id"],
    )
    return {"memory_note": memory_note}


def record_node(state: RcaState, config: RunnableConfig) -> dict[str, Any]:
    logger: RunLogger = _cfg(config)["logger"]
    brief = state["decision_brief"]
    monitoring = brief.get("monitoring_plan") or {}
    record_outcome(
        OutcomeRecord(
            run_id=state["run_id"],
            city_id=state["city_id"],
            dt=state["dt"],
            signal_label=str(state["signal_evidence"].get("signal_label") or ""),
            confidence=str(brief.get("confidence") or "low"),
            headline=str(brief.get("headline") or ""),
            decision_card_markdown=state["decision_card_markdown"],
            report_markdown=state["report_markdown"],
            prediction_markdown=state["prediction_markdown"],
            prescription_markdown=state["prescription_markdown"],
            status="complete",
            round_count=state["round_count"],
            decision_brief_json=brief,
            hypotheses_json=[],
            evidence_ledger_json=state["evidence_ledger"],
            investigation_rounds_json=state["investigation_rounds"],
            critic_reviews_json=state["critic_reviews"],
            monitoring_plan_json=monitoring if isinstance(monitoring, dict) else {},
            evaluation_json=state["evaluation"],
            memory_context_json=state["memory_context"],
        )
    )
    logger.log(actor_type="workflow", actor_name="rca_run", action="completed", source="system", details={})
    logger.flush_to_supabase()
    return {}


def build_rca_graph() -> Any:
    builder: StateGraph = StateGraph(RcaState)
    builder.add_node("investigation_loop", investigation_loop_node)
    builder.add_node("decision", decision_node)
    builder.add_node("evaluation", evaluation_node)
    builder.add_node("memory", memory_node)
    builder.add_node("record", record_node)

    builder.add_edge(START, "investigation_loop")
    builder.add_edge("investigation_loop", "decision")
    builder.add_edge("decision", "evaluation")
    builder.add_edge("evaluation", "memory")
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
            "investigation_rounds": [],
            "evidence_ledger": [],
            "critic_reviews": [],
            "round_count": 0,
            "memory_context": {},
            "decision_brief": {},
            "decision_card_markdown": "",
            "report_markdown": "",
            "prediction_markdown": "",
            "prescription_markdown": "",
            "evaluation": {},
            "memory_note": "",
        },
        config={"configurable": {"settings": settings, "client_factory": base_factory, "logger": logger}},
    )
    return {
        "run_id": run_id,
        "signal_evidence": final_state["signal_evidence"],
        "round_count": final_state["round_count"],
        "decision_brief": final_state["decision_brief"],
        "final_report": final_state["decision_card_markdown"],  # backward compat for CLI
        "decision_card_markdown": final_state["decision_card_markdown"],
        "evidence_ledger": final_state["evidence_ledger"],
        "investigation_rounds": final_state["investigation_rounds"],
        "memory_note": final_state["memory_note"],
        "evaluation": final_state["evaluation"],
    }
