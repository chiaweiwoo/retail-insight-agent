"""LangGraph orchestration for the RCA pipeline.

Replaces the ThreadPoolExecutor-based run_coordinator with a StateGraph that
uses the Send API for true parallel fan-out of specialist analysts.

Entry point: run_rca_graph() — same signature as agents.run_coordinator().
"""
from __future__ import annotations

import json
import operator
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Callable

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from typing_extensions import TypedDict

from rca.agents import (
    AnalystRunResult,
    AnalystSpec,
    CoordinatorResult,
    _plan_specialists_with_reasons,
    _run_critic,
    _run_finance_controller,
    _run_slt_brief,
    _run_specialist,
    _synthesize,
)
from rca.profiles import get_store_profile
from rca.llm import (
    ClientFactory,
    LLMSettings,
    build_chat_completion_kwargs,
    build_openai_compatible_client,
    load_llm_settings,
    make_routed_settings,
)
from rca.obs import RcaObserver
from rca.outcomes import build_outcome_record, get_prior_rca, record_outcome
from rca.report import render_markdown_document, sanitize_generated_markdown
from rca.runlog import RunLogger
from rca.tools import get_signal_evidence


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class RcaState(TypedDict):
    city_id: int
    dt: str
    run_name: str
    output_dir_str: str | None
    include_research: bool

    # Populated by plan_node
    specialists: list[dict]      # list of asdict(AnalystSpec)
    planning_inputs: dict | None
    prior_rca_summary: dict
    skipped_analysts: list[dict]

    # Fetched in plan_node, threaded into all LLM preambles
    store_profile: str | None

    # Whether to run the optional reflection pass after the SLT brief
    enable_reflection: bool

    # Accumulated via Send fan-out (operator.add merges results from each branch)
    analyst_results: Annotated[list[dict], operator.add]

    # Populated by downstream nodes
    critic_note: str
    coordinator_report: str
    controller_note: str
    decision_card: str
    reflection_note: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _cfg(config: RunnableConfig) -> dict[str, Any]:
    return config.get("configurable") or {}


def _restore_analyst_results(state: RcaState) -> list[AnalystRunResult]:
    """Reconstruct typed AnalystRunResult objects, preserving specialist order."""
    specialist_names = [s["name"] for s in state["specialists"]]
    by_name = {r["name"]: r for r in state["analyst_results"]}
    ordered = [by_name[name] for name in specialist_names if name in by_name]
    return [
        AnalystRunResult(
            name=r["name"],
            focus=r["focus"],
            memo_markdown=r["memo_markdown"],
            tool_calls=r["tool_calls"],
        )
        for r in ordered
    ]


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------


def plan_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    logger: RunLogger = cfg["logger"]
    observer: RcaObserver = cfg["observer"]
    city_id = state["city_id"]
    dt = state["dt"]
    include_research = state.get("include_research", False)
    subject = f"{city_id}:{dt}"

    with observer.node_span("plan"):
        prior_rca_summary = get_prior_rca(city_id)
        store_profile = get_store_profile(city_id)

        if state.get("specialists"):
            # Pre-specified by caller — skip re-planning, use as-is
            logger.log(
                actor_type="workflow", actor_name="coordinator_pipeline",
                action="started", subject=subject, source="system",
                details={"analyst_count": len(state["specialists"]), "planning_inputs": None, "prior_rca_summary": prior_rca_summary, "has_store_profile": store_profile is not None},
            )
            return {"prior_rca_summary": prior_rca_summary, "planning_inputs": None, "skipped_analysts": [], "store_profile": store_profile}

        specialists, skipped_analysts, planning_inputs = _plan_specialists_with_reasons(
            city_id=city_id, dt=dt, include_research=include_research
        )

        logger.log(
            actor_type="workflow", actor_name="coordinator_pipeline",
            action="started", subject=subject, source="system",
            details={"analyst_count": len(specialists), "planning_inputs": planning_inputs, "prior_rca_summary": prior_rca_summary, "has_store_profile": store_profile is not None},
        )
        logger.log(
            actor_type="workflow", actor_name="plan_specialists",
            action="completed", subject=subject, source="system",
            details={
                "selected_analysts": [s.name for s in specialists],
                "skipped_analysts": skipped_analysts,
                "include_research": include_research,
                "prior_rca_summary": prior_rca_summary,
            },
        )

        return {
            "specialists": [asdict(s) for s in specialists],
            "planning_inputs": planning_inputs,
            "prior_rca_summary": prior_rca_summary,
            "skipped_analysts": skipped_analysts,
            "store_profile": store_profile,
        }


def route_specialists(state: RcaState) -> list[Send]:
    return [
        Send(
            "run_specialist",
            {
                "spec_dict": spec_dict,
                "city_id": state["city_id"],
                "dt": state["dt"],
            },
        )
        for spec_dict in state["specialists"]
    ]


def run_specialist_node(state: dict, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    base_settings: LLMSettings = cfg["settings"]
    client_factory: ClientFactory = cfg["client_factory"]
    logger: RunLogger = cfg["logger"]
    observer: RcaObserver = cfg["observer"]

    spec_dict = state["spec_dict"]
    spec = AnalystSpec(
        name=spec_dict["name"],
        focus=spec_dict["focus"],
        tool_names=tuple(spec_dict["tool_names"]),
        system_prompt=spec_dict["system_prompt"],
    )
    node_settings = make_routed_settings(base_settings, spec.name)

    with observer.node_span(spec.name):
        result = _run_specialist(
            spec=spec,
            city_id=state["city_id"],
            dt=state["dt"],
            settings=node_settings,
            logger=logger,
            client_factory=client_factory,
            profile_text=state.get("store_profile"),
        )
    result_dict = asdict(result)
    result_dict["memo_markdown"] = sanitize_generated_markdown(result_dict["memo_markdown"])
    return {"analyst_results": [result_dict]}


def critic_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    base_settings: LLMSettings = cfg["settings"]
    client_factory: ClientFactory = cfg["client_factory"]
    logger: RunLogger = cfg["logger"]
    observer: RcaObserver = cfg["observer"]
    subject = f"{state['city_id']}:{state['dt']}"

    analyst_results = _restore_analyst_results(state)
    logger.log(
        actor_type="workflow", actor_name="coordinator_pipeline",
        action="analysts_completed", subject=subject, source="system",
        details={
            "analysts": [r.name for r in analyst_results],
            "tool_call_counts": {r.name: len(r.tool_calls) for r in analyst_results},
        },
    )

    node_settings = make_routed_settings(base_settings, "critic")
    with observer.node_span("critic"):
        critic_note = _run_critic(
            city_id=state["city_id"],
            dt=state["dt"],
            analyst_results=analyst_results,
            settings=node_settings,
            logger=logger,
            client_factory=client_factory,
            profile_text=state.get("store_profile"),
        )
    logger.log(
        actor_type="workflow", actor_name="coordinator_pipeline",
        action="critic_completed", subject=subject, source="system",
        details={"critic_note_preview": critic_note[:200]},
    )
    return {"critic_note": critic_note}


def synthesize_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    base_settings: LLMSettings = cfg["settings"]
    client_factory: ClientFactory = cfg["client_factory"]
    logger: RunLogger = cfg["logger"]
    observer: RcaObserver = cfg["observer"]

    analyst_results = _restore_analyst_results(state)
    node_settings = make_routed_settings(base_settings, "coordinator_analyst")

    with observer.node_span("synthesize"):
        coordinator_report = _synthesize(
            city_id=state["city_id"],
            dt=state["dt"],
            analyst_results=analyst_results,
            critic_note_markdown=state["critic_note"],
            settings=node_settings,
            logger=logger,
            client_factory=client_factory,
            profile_text=state.get("store_profile"),
        )
    return {"coordinator_report": coordinator_report}


def controller_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    base_settings: LLMSettings = cfg["settings"]
    client_factory: ClientFactory = cfg["client_factory"]
    logger: RunLogger = cfg["logger"]
    observer: RcaObserver = cfg["observer"]
    node_settings = make_routed_settings(base_settings, "finance_controller")

    with observer.node_span("controller"):
        controller_note = _run_finance_controller(
            city_id=state["city_id"],
            dt=state["dt"],
            coordinator_report_markdown=state["coordinator_report"],
            critic_note_markdown=state["critic_note"],
            settings=node_settings,
            logger=logger,
            client_factory=client_factory,
            profile_text=state.get("store_profile"),
        )
    return {"controller_note": controller_note}


def slt_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    base_settings: LLMSettings = cfg["settings"]
    client_factory: ClientFactory = cfg["client_factory"]
    logger: RunLogger = cfg["logger"]
    observer: RcaObserver = cfg["observer"]
    node_settings = make_routed_settings(base_settings, "slt_brief")

    with observer.node_span("slt"):
        decision_card = _run_slt_brief(
            city_id=state["city_id"],
            dt=state["dt"],
            coordinator_report_markdown=state["coordinator_report"],
            controller_note_markdown=state["controller_note"],
            critic_note_markdown=state["critic_note"],
            prior_rca_summary=state["prior_rca_summary"],
            settings=node_settings,
            logger=logger,
            client_factory=client_factory,
            profile_text=state.get("store_profile"),
        )
    return {"decision_card": decision_card}


_REFLECTION_SYSTEM_PROMPT = """\
You are auditing a retail RCA decision for hidden assumptions and data gaps.

Identify the SINGLE weakest assumption or most consequential missing evidence. Then write:
1. What the assumption is
2. What specific data or observation would confirm or refute it
3. Whether this uncertainty changes the recommended action

Rules:
- Exactly 3 bullets, no more
- Cite specific figures from the decision card if available
- Use normalized sales amounts, not currency
- Plain ASCII markdown, start with "## Reflection"
- If the analysis is well-supported, say so plainly in bullet 1
"""


def _route_after_slt(state: RcaState) -> str:
    return "reflect" if state.get("enable_reflection") else "sanitize"


def reflect_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    base_settings: LLMSettings = cfg["settings"]
    client_factory: ClientFactory = cfg["client_factory"]
    logger: RunLogger = cfg["logger"]
    observer: RcaObserver = cfg["observer"]
    subject = f"{state['city_id']}:{state['dt']}"

    node_settings = make_routed_settings(base_settings, "reflect")
    client = client_factory("reflect")

    messages = [
        {"role": "system", "content": _REFLECTION_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Decision card:\n{state['decision_card']}\n\n"
                f"RCA report (excerpt):\n{state['coordinator_report'][:2000]}\n\n"
                f"Critic note (excerpt):\n{state['critic_note'][:800]}"
            ),
        },
    ]
    logger.log(
        actor_type="llm", actor_name="reflect",
        action="completion_requested", subject=subject, source="llm", details={},
    )
    with observer.node_span("reflect"):
        response = client.chat.completions.create(
            **build_chat_completion_kwargs(node_settings, messages, tools=None)
        )
    content = response.choices[0].message.content or ""
    logger.log(
        actor_type="llm", actor_name="reflect",
        action="completion_finished", subject=subject, source="llm",
        details={"content_preview": content[:200]},
    )
    return {"reflection_note": content}


def sanitize_node(state: RcaState) -> dict:
    """Sanitize synthesis artifacts (specialist memos already sanitized at generation)."""
    result: dict = {
        "coordinator_report": sanitize_generated_markdown(state["coordinator_report"]),
        "critic_note": sanitize_generated_markdown(state["critic_note"]),
        "controller_note": sanitize_generated_markdown(state["controller_note"]),
        "decision_card": sanitize_generated_markdown(state["decision_card"]),
    }
    if state.get("reflection_note"):
        result["reflection_note"] = sanitize_generated_markdown(state["reflection_note"])
    return result


def record_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    logger: RunLogger = cfg["logger"]
    is_dry_run: bool = cfg.get("is_dry_run", False)
    subject = f"{state['city_id']}:{state['dt']}"

    signal_evidence = (
        (state.get("planning_inputs") or {}).get("signal_evidence")
        or get_signal_evidence(state["city_id"], state["dt"])
    )
    outcome_record = build_outcome_record(
        run_name=state["run_name"],
        city_id=state["city_id"],
        dt=state["dt"],
        signal_evidence=signal_evidence,
        coordinator_report_markdown=state["coordinator_report"],
        decision_card_markdown=state["decision_card"],
    )
    record_outcome(outcome_record, dry_run=is_dry_run)
    logger.log(
        actor_type="workflow", actor_name="coordinator_pipeline",
        action="outcome_recorded", subject=subject, source="system",
        details={
            "signal_label": outcome_record.signal_label,
            "top_driver": outcome_record.top_driver,
            "driver_class": outcome_record.driver_class,
            "confidence": outcome_record.confidence,
            "escalated": outcome_record.escalated,
        },
    )
    logger.log(
        actor_type="workflow", actor_name="coordinator_pipeline",
        action="completed", subject=subject, source="system",
        details={
            "analyst_count": len(state["analyst_results"]),
            "output_dir": state.get("output_dir_str"),
        },
    )
    return {}


def artifacts_node(state: RcaState, config: RunnableConfig) -> dict:
    cfg = _cfg(config)
    logger: RunLogger = cfg["logger"]
    output_dir_str = state.get("output_dir_str")

    if output_dir_str is None:
        return {}

    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "run_log.jsonl").write_text(logger.to_jsonl(), encoding="utf-8")
    (output_dir / "run_log.md").write_text(logger.to_markdown(), encoding="utf-8")

    city_id = state["city_id"]
    dt = state["dt"]

    specialist_dir = output_dir / "specialists"
    specialist_dir.mkdir(parents=True, exist_ok=True)
    for r in state["analyst_results"]:
        name = r["name"]
        memo = r["memo_markdown"]
        (specialist_dir / f"{name}.md").write_text(memo, encoding="utf-8")
        (specialist_dir / f"{name}.html").write_text(
            render_markdown_document(memo, title=f"{name} memo for {city_id} on {dt}"),
            encoding="utf-8",
        )

    def _write_pair(stem: str, content: str, title: str) -> None:
        (output_dir / f"{stem}.md").write_text(content, encoding="utf-8")
        (output_dir / f"{stem}.html").write_text(
            render_markdown_document(content, title=title), encoding="utf-8"
        )

    _write_pair("critique", state["critic_note"], f"Critique for {city_id} on {dt}")
    _write_pair("controller_note", state["controller_note"], f"Finance controller note for {city_id} on {dt}")
    _write_pair("decision_card", state["decision_card"], f"Decision card for {city_id} on {dt}")
    _write_pair("report", state["coordinator_report"], f"RCA report for {city_id} on {dt}")
    reflection_note = state.get("reflection_note", "")
    if reflection_note:
        _write_pair("reflection", reflection_note, f"Reflection for {city_id} on {dt}")

    trace_payload = {
        "city_id": city_id,
        "dt": dt,
        "planner": {
            "selected_analysts": [s["name"] for s in state["specialists"]],
            "skipped_analysts": state.get("skipped_analysts", []),
            "include_research": state.get("include_research", False),
            "planning_inputs": state.get("planning_inputs"),
            "prior_rca_summary": state.get("prior_rca_summary", {}),
        },
        "critic_note_markdown": state["critic_note"],
        "controller_note_markdown": state["controller_note"],
        "decision_card_markdown": state["decision_card"],
        "coordinator_report_markdown": state["coordinator_report"],
        "reflection_note_markdown": state.get("reflection_note", ""),
        "analyst_results": state["analyst_results"],
    }
    trace_json = json.dumps(trace_payload, indent=2, ensure_ascii=False)
    (output_dir / "coordinator_trace.json").write_text(trace_json, encoding="utf-8")
    (output_dir / "run_trace.json").write_text(trace_json, encoding="utf-8")

    return {}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------


def build_rca_graph() -> Any:
    builder: StateGraph = StateGraph(RcaState)
    builder.add_node("plan", plan_node)
    builder.add_node("run_specialist", run_specialist_node)
    builder.add_node("critic", critic_node)
    builder.add_node("synthesize", synthesize_node)
    builder.add_node("controller", controller_node)
    builder.add_node("slt", slt_node)
    builder.add_node("reflect", reflect_node)
    builder.add_node("sanitize", sanitize_node)
    builder.add_node("record", record_node)
    builder.add_node("artifacts", artifacts_node)

    builder.add_edge(START, "plan")
    builder.add_conditional_edges("plan", route_specialists, ["run_specialist"])
    builder.add_edge("run_specialist", "critic")
    builder.add_edge("critic", "synthesize")
    builder.add_edge("synthesize", "controller")
    builder.add_edge("controller", "slt")
    builder.add_conditional_edges("slt", _route_after_slt, ["reflect", "sanitize"])
    builder.add_edge("reflect", "sanitize")
    builder.add_edge("sanitize", "record")
    builder.add_edge("record", "artifacts")
    builder.add_edge("artifacts", END)

    return builder.compile()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_rca_graph(
    city_id: int,
    dt: str,
    specialists: list[AnalystSpec] | None = None,
    settings: LLMSettings | None = None,
    client_factory: ClientFactory | None = None,
    output_dir: Path | None = None,
    include_research: bool = False,
    enable_reflection: bool = False,
) -> CoordinatorResult:
    settings = settings or load_llm_settings()
    is_dry_run = client_factory is not None
    run_name = f"{city_id}_{dt}"
    logger = RunLogger(run_name=run_name)

    base_factory: ClientFactory = client_factory or (lambda node_name: build_openai_compatible_client(settings))
    observer = RcaObserver(city_id=city_id, dt=dt, run_name=run_name, is_dry_run=is_dry_run)
    traced_factory = observer.wrap_client_factory(base_factory)

    initial_state: dict = {
        "city_id": city_id,
        "dt": dt,
        "run_name": run_name,
        "output_dir_str": str(output_dir) if output_dir is not None else None,
        "include_research": include_research,
        "specialists": [asdict(s) for s in specialists] if specialists is not None else [],
        "planning_inputs": None,
        "prior_rca_summary": {},
        "skipped_analysts": [],
        "store_profile": None,
        "enable_reflection": enable_reflection,
        "analyst_results": [],
        "critic_note": "",
        "coordinator_report": "",
        "controller_note": "",
        "decision_card": "",
        "reflection_note": "",
    }

    graph_config: dict = {
        "configurable": {
            "settings": settings,
            "client_factory": traced_factory,
            "logger": logger,
            "observer": observer,
            "is_dry_run": is_dry_run,
        }
    }

    graph = build_rca_graph()
    final_state: RcaState = graph.invoke(initial_state, config=graph_config)
    observer.finalize(output={"city_id": city_id, "dt": dt})

    analyst_results = _restore_analyst_results(final_state)
    return CoordinatorResult(
        city_id=final_state["city_id"],
        dt=final_state["dt"],
        coordinator_report_markdown=final_state["coordinator_report"],
        critic_note_markdown=final_state["critic_note"],
        controller_note_markdown=final_state["controller_note"],
        decision_card_markdown=final_state["decision_card"],
        analyst_results=analyst_results,
    )
