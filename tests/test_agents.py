"""Unit tests for Phase 2 agent components.

All tests here are pure Python — no Supabase calls, no LLM calls.
The investigation loop integration tests use monkeypatching.
"""
from __future__ import annotations

import pytest

from rca.agents import (
    AgentRunResult,
    PlannerDecision,
    _make_investigation_key,
    agent_memo_to_evidence_items,
)
from rca.state import (
    CriticReview,
    DecisionBrief,
    MonitoringPlan,
    RcaRunState,
)


# ── PlannerDecision ───────────────────────────────────────────────────────────


def test_planner_decision_new_fields_have_defaults() -> None:
    decision = PlannerDecision(
        selected_agents=["statistician"],
        rationale="test",
        news_query="",
    )
    assert decision.objective == ""
    assert decision.target_gaps == []
    assert decision.expected_evidence == []


def test_planner_decision_new_fields_accept_values() -> None:
    decision = PlannerDecision(
        selected_agents=["statistician", "sales_agent"],
        rationale="Investigate drop.",
        news_query="city 0 retail news",
        objective="Validate the drop signal.",
        target_gaps=["gap_001"],
        expected_evidence=["sales trend", "inventory pressure"],
    )
    assert decision.objective == "Validate the drop signal."
    assert decision.target_gaps == ["gap_001"]
    assert decision.expected_evidence == ["sales trend", "inventory pressure"]


# ── AgentRunResult ────────────────────────────────────────────────────────────


def test_agent_run_result_evidence_items_defaults_empty() -> None:
    result = AgentRunResult(
        name="sales_agent",
        focus="explain sales movement",
        memo_markdown="## Evidence\nSales dropped.",
        tool_calls=[],
    )
    assert result.evidence_items == []


# ── Repetition guard key ──────────────────────────────────────────────────────


def test_make_investigation_key_no_gaps_returns_initial() -> None:
    key = _make_investigation_key("inventory_agent", [])
    assert key == "inventory_agent__initial"


def test_make_investigation_key_with_gaps_is_sorted() -> None:
    key_a = _make_investigation_key("inventory_agent", ["gap_003", "gap_001"])
    key_b = _make_investigation_key("inventory_agent", ["gap_001", "gap_003"])
    assert key_a == key_b


def test_make_investigation_key_different_agents_differ() -> None:
    key_a = _make_investigation_key("inventory_agent", ["gap_001"])
    key_b = _make_investigation_key("pricing_agent", ["gap_001"])
    assert key_a != key_b


# ── agent_memo_to_evidence_items ──────────────────────────────────────────────


def test_agent_memo_one_tool_call_plus_memo_produces_two_items() -> None:
    result = AgentRunResult(
        name="inventory_agent",
        focus="assess inventory",
        memo_markdown="## Evidence\nStockout rate was 35%.",
        tool_calls=[
            {
                "id": "tc1",
                "name": "get_inventory_context",
                "arguments": {"city_id": 0, "dt": "2024-05-16"},
                "result": {"stockout_product_rate": 0.35},
            }
        ],
    )
    state = RcaRunState(run_id="test", city_id=0, dt="2024-05-16")
    items = agent_memo_to_evidence_items(result, state)

    assert len(items) == 2
    assert items[0].id == "ev_001"
    assert items[0].evidence_type == "observation"
    assert items[0].tool_name == "get_inventory_context"
    assert items[0].agent_name == "inventory_agent"
    assert items[1].id == "ev_002"
    assert items[1].evidence_type == "inference"
    assert items[1].agent_name == "inventory_agent"


def test_agent_memo_no_tool_calls_produces_one_item() -> None:
    result = AgentRunResult(
        name="news_agent",
        focus="external events",
        memo_markdown="## Evidence\nNo external events found.",
        tool_calls=[],
    )
    state = RcaRunState(run_id="test", city_id=0, dt="2024-05-16")
    items = agent_memo_to_evidence_items(result, state)

    assert len(items) == 1
    assert items[0].id == "ev_001"
    assert items[0].evidence_type == "inference"


def test_agent_memo_multiple_tool_calls_all_become_observations() -> None:
    result = AgentRunResult(
        name="statistician",
        focus="validate signal",
        memo_markdown="## Evidence\nBaseline confirmed.",
        tool_calls=[
            {"id": "t1", "name": "get_signal_evidence", "arguments": {}, "result": {}},
            {"id": "t2", "name": "get_sales_context", "arguments": {}, "result": {}},
        ],
    )
    state = RcaRunState(run_id="test", city_id=0, dt="2024-05-16")
    items = agent_memo_to_evidence_items(result, state)

    assert len(items) == 3  # 2 tool calls + 1 memo
    assert items[0].evidence_type == "observation"
    assert items[1].evidence_type == "observation"
    assert items[2].evidence_type == "inference"


def test_agent_memo_ids_are_sequential_across_agents() -> None:
    state = RcaRunState(run_id="test", city_id=0, dt="2024-05-16")

    result_a = AgentRunResult(name="sales_agent", focus="sales", memo_markdown="OK.", tool_calls=[])
    result_b = AgentRunResult(name="inventory_agent", focus="inv", memo_markdown="OK.", tool_calls=[])

    items_a = agent_memo_to_evidence_items(result_a, state)
    items_b = agent_memo_to_evidence_items(result_b, state)

    assert items_a[0].id == "ev_001"
    assert items_b[0].id == "ev_002"


def test_agent_memo_empty_memo_produces_no_inference_item() -> None:
    result = AgentRunResult(
        name="sales_agent",
        focus="sales",
        memo_markdown="",
        tool_calls=[{"id": "t1", "name": "get_sales_context", "arguments": {}, "result": {}}],
    )
    state = RcaRunState(run_id="test", city_id=0, dt="2024-05-16")
    items = agent_memo_to_evidence_items(result, state)
    assert len(items) == 1
    assert items[0].evidence_type == "observation"


def test_agent_memo_tool_result_dict_is_payload() -> None:
    payload = {"stockout_product_rate": 0.35, "total_sales": 100.0}
    result = AgentRunResult(
        name="inventory_agent",
        focus="inventory",
        memo_markdown="",
        tool_calls=[{"id": "t1", "name": "get_inventory_context", "arguments": {}, "result": payload}],
    )
    state = RcaRunState(run_id="test", city_id=0, dt="2024-05-16")
    items = agent_memo_to_evidence_items(result, state)
    assert items[0].payload == payload


def test_agent_memo_non_dict_tool_result_wrapped() -> None:
    result = AgentRunResult(
        name="sales_agent",
        focus="sales",
        memo_markdown="",
        tool_calls=[{"id": "t1", "name": "get_sales_context", "arguments": {}, "result": "some string"}],
    )
    state = RcaRunState(run_id="test", city_id=0, dt="2024-05-16")
    items = agent_memo_to_evidence_items(result, state)
    assert items[0].payload == {"raw": "some string"}


# ── CriticReview model ────────────────────────────────────────────────────────


def test_critic_review_continue_false_serialises() -> None:
    review = CriticReview(
        round_index=1,
        continue_investigation=False,
        confidence_ceiling="medium",
        stop_reason="Sufficient evidence.",
    )
    d = review.model_dump(mode="json")
    assert d["round_index"] == 1
    assert d["continue_investigation"] is False
    assert d["stop_reason"] == "Sufficient evidence."


def test_critic_review_with_gaps_serialises() -> None:
    from rca.state import CriticGap

    gap = CriticGap(
        id="gap_001",
        description="No inventory data checked.",
        severity="high",
        gap_type="missing_internal_evidence",
        suggested_agents=["inventory_agent"],
    )
    review = CriticReview(
        round_index=2,
        continue_investigation=True,
        confidence_ceiling="low",
        gaps=[gap],
    )
    d = review.model_dump(mode="json")
    assert d["continue_investigation"] is True
    assert d["gaps"][0]["gap_type"] == "missing_internal_evidence"
    assert d["gaps"][0]["suggested_agents"] == ["inventory_agent"]


# ── DecisionBrief model ───────────────────────────────────────────────────────


def test_decision_brief_monitoring_plan_serialises() -> None:
    plan = MonitoringPlan(
        metrics_to_watch=["stockout_product_rate", "total_sales"],
        review_horizon="7 days",
        escalation_trigger="drop repeats next cycle",
    )
    brief = DecisionBrief(
        headline="Sales drop driven by inventory.",
        confidence="medium",
        situation="City 0 recorded a 20% drop vs baseline.",
        business_impact="Normalized sales below baseline.",
        most_likely_explanation="Stockout pressure during peak hours.",
        recommended_action="Review replenishment schedule.",
        owner_function="Operations",
        urgency="medium",
        expected_benefit="Reduce recurrence risk.",
        monitoring_plan=plan,
    )
    d = brief.model_dump(mode="json")
    assert d["confidence"] == "medium"
    assert d["monitoring_plan"]["review_horizon"] == "7 days"
    assert "stockout_product_rate" in d["monitoring_plan"]["metrics_to_watch"]


def test_decision_brief_unknowns_and_caveats() -> None:
    brief = DecisionBrief(
        headline="Test",
        confidence="low",
        situation=".",
        business_impact=".",
        most_likely_explanation="Insufficient evidence.",
        recommended_action="Re-run.",
        owner_function="Analytics",
        urgency="low",
        expected_benefit=".",
        unknowns=["Margin data unavailable."],
        caveats=["Synthetic goals used."],
    )
    d = brief.model_dump(mode="json")
    assert d["unknowns"] == ["Margin data unavailable."]
    assert d["caveats"] == ["Synthetic goals used."]


# ── Investigation loop with mocked dependencies ───────────────────────────────


def test_investigation_loop_runs_one_round(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loop runs exactly one round when critic says stop."""
    from rca.agents import run_investigation_loop
    from rca.llm import LLMSettings
    from rca.runlog import RunLogger

    settings = LLMSettings(api_key="x", base_url="http://localhost", model="test", thinking_enabled=False)
    logger = RunLogger(run_id="test", city_id=0, dt="2024-05-16")

    monkeypatch.setattr(
        "rca.agents.plan_investigation",
        lambda **kw: PlannerDecision(
            selected_agents=["statistician"], rationale="test", news_query="", objective="Validate drop signal."
        ),
    )
    monkeypatch.setattr(
        "rca.agents._run_agents_parallel",
        lambda **kw: [AgentRunResult(name="statistician", focus="validate signal", memo_markdown="## Evidence\nSales dropped.", tool_calls=[])],
    )
    monkeypatch.setattr(
        "rca.agents.run_critic",
        lambda **kw: CriticReview(round_index=kw["round_index"], continue_investigation=False, confidence_ceiling="medium", stop_reason="Done."),  # type: ignore[arg-type]
    )

    state = run_investigation_loop(
        city_id=0,
        dt="2024-05-16",
        signal_evidence={"signal_label": "drop", "city_id": 0, "dt": "2024-05-16"},
        memory_notes=[],
        run_id="test",
        settings=settings,
        logger=logger,
        client_factory=lambda n: None,
    )

    assert len(state.investigation_rounds) == 1
    assert state.investigation_rounds[0].objective == "Validate drop signal."
    assert state.investigation_rounds[0].completed_agents == ["statistician"]
    assert len(state.evidence_ledger) == 1  # 1 memo item, no tool calls


def test_investigation_loop_critic_continue_adds_second_round(monkeypatch: pytest.MonkeyPatch) -> None:
    """Critic identifies a gap in round 1 → planner targets it with a different agent in round 2."""
    from rca.agents import run_investigation_loop
    from rca.llm import LLMSettings
    from rca.runlog import RunLogger
    from rca.state import CriticGap

    settings = LLMSettings(api_key="x", base_url="http://localhost", model="test", thinking_enabled=False)
    logger = RunLogger(run_id="test", city_id=0, dt="2024-05-16")

    gap = CriticGap(
        id="gap_001",
        description="Inventory not yet checked.",
        severity="high",
        gap_type="missing_internal_evidence",
        suggested_agents=["inventory_agent"],
    )

    call_count = {"n": 0}

    def _planner(**kw: object) -> PlannerDecision:
        call_count["n"] += 1
        # Round 1: statistician. Round 2: inventory_agent (targeting gap_001).
        if call_count["n"] == 1:
            return PlannerDecision(
                selected_agents=["statistician"], rationale="", news_query="", objective="Round 1"
            )
        return PlannerDecision(
            selected_agents=["inventory_agent"],
            rationale="",
            news_query="",
            objective="Round 2 — address gap_001",
            target_gaps=["gap_001"],
        )

    def _critic(**kw: object) -> CriticReview:
        round_index: int = kw["round_index"]  # type: ignore[assignment]
        # Round 1: continue with a gap. Round 2: stop.
        if round_index == 1:
            return CriticReview(
                round_index=1,
                continue_investigation=True,
                confidence_ceiling="low",
                gaps=[gap],
            )
        return CriticReview(
            round_index=2,
            continue_investigation=False,
            confidence_ceiling="medium",
            stop_reason="Gap addressed.",
        )

    def _agents(**kw: object) -> list[AgentRunResult]:
        agent_names: list[str] = kw["agent_names"]  # type: ignore[assignment]
        return [AgentRunResult(name=n, focus="f", memo_markdown="OK.", tool_calls=[]) for n in agent_names]

    monkeypatch.setattr("rca.agents.plan_investigation", _planner)
    monkeypatch.setattr("rca.agents._run_agents_parallel", _agents)
    monkeypatch.setattr("rca.agents.run_critic", _critic)

    state = run_investigation_loop(
        city_id=0,
        dt="2024-05-16",
        signal_evidence={"signal_label": "drop"},
        memory_notes=[],
        run_id="test",
        settings=settings,
        logger=logger,
        client_factory=lambda n: None,
    )

    assert len(state.investigation_rounds) == 2
    assert state.investigation_rounds[0].completed_agents == ["statistician"]
    assert state.investigation_rounds[1].completed_agents == ["inventory_agent"]


def test_investigation_loop_stops_at_max_rounds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loop never exceeds max_rounds even when critic keeps saying continue.

    Three distinct agents used (one per round) so the repetition guard never blocks.
    """
    from rca.agents import run_investigation_loop
    from rca.llm import LLMSettings
    from rca.runlog import RunLogger

    settings = LLMSettings(api_key="x", base_url="http://localhost", model="test", thinking_enabled=False)
    logger = RunLogger(run_id="test", city_id=0, dt="2024-05-16")

    agent_rotation = ["statistician", "sales_agent", "pricing_agent"]
    call_count = {"n": 0}

    def _planner(**kw: object) -> PlannerDecision:
        agent = agent_rotation[call_count["n"] % len(agent_rotation)]
        return PlannerDecision(
            selected_agents=[agent],
            rationale="keep going",
            news_query="",
            objective=f"Round {call_count['n'] + 1}",
        )

    def _agents(**kw: object) -> list[AgentRunResult]:
        agent_names: list[str] = kw["agent_names"]  # type: ignore[assignment]
        call_count["n"] += 1
        return [AgentRunResult(name=n, focus="f", memo_markdown="OK.", tool_calls=[]) for n in agent_names]

    monkeypatch.setattr("rca.agents.plan_investigation", _planner)
    monkeypatch.setattr("rca.agents._run_agents_parallel", _agents)
    monkeypatch.setattr(
        "rca.agents.run_critic",
        lambda **kw: CriticReview(round_index=kw["round_index"], continue_investigation=True, confidence_ceiling="low"),  # type: ignore[arg-type]
    )

    state = run_investigation_loop(
        city_id=0,
        dt="2024-05-16",
        signal_evidence={"signal_label": "drop"},
        memory_notes=[],
        run_id="test",
        settings=settings,
        logger=logger,
        client_factory=lambda n: None,
        max_rounds=3,
    )

    assert len(state.investigation_rounds) == 3


def test_investigation_loop_repetition_guard_breaks_early(monkeypatch: pytest.MonkeyPatch) -> None:
    """After round 1, same agent+gap combo is blocked; loop exits early."""
    from rca.agents import run_investigation_loop
    from rca.llm import LLMSettings
    from rca.runlog import RunLogger

    settings = LLMSettings(api_key="x", base_url="http://localhost", model="test", thinking_enabled=False)
    logger = RunLogger(run_id="test", city_id=0, dt="2024-05-16")

    monkeypatch.setattr(
        "rca.agents.plan_investigation",
        lambda **kw: PlannerDecision(
            selected_agents=["sales_agent"], rationale="test", news_query="", objective="Same agent again."
        ),
    )
    monkeypatch.setattr(
        "rca.agents._run_agents_parallel",
        lambda **kw: [AgentRunResult(name="sales_agent", focus="f", memo_markdown="OK.", tool_calls=[])],
    )
    monkeypatch.setattr(
        "rca.agents.run_critic",
        lambda **kw: CriticReview(round_index=kw["round_index"], continue_investigation=True, confidence_ceiling="low"),  # type: ignore[arg-type]
    )

    state = run_investigation_loop(
        city_id=0,
        dt="2024-05-16",
        signal_evidence={"signal_label": "drop"},
        memory_notes=[],
        run_id="test",
        settings=settings,
        logger=logger,
        client_factory=lambda n: None,
        max_rounds=5,
    )

    # Round 1 runs; round 2 is blocked because sales_agent__initial is already used
    assert len(state.investigation_rounds) == 1


def test_news_agent_excluded_round1_no_prior_external_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    """news_agent must not run in round 1 — no prior external gap from critic."""
    import os

    from rca.agents import run_investigation_loop
    from rca.llm import LLMSettings
    from rca.runlog import RunLogger

    settings = LLMSettings(api_key="x", base_url="http://localhost", model="test", thinking_enabled=False)
    logger = RunLogger(run_id="test", city_id=0, dt="2024-05-16")

    dispatched: list[str] = []

    def _agents(**kw: object) -> list[AgentRunResult]:
        agent_names: list[str] = kw["agent_names"]  # type: ignore[assignment]
        dispatched.extend(agent_names)
        return [AgentRunResult(name=n, focus="f", memo_markdown="OK.", tool_calls=[]) for n in agent_names]

    monkeypatch.setattr(
        "rca.agents.plan_investigation",
        lambda **kw: PlannerDecision(
            selected_agents=["statistician", "news_agent"], rationale="test", news_query="q", objective="R1"
        ),
    )
    monkeypatch.setattr("rca.agents._run_agents_parallel", _agents)
    monkeypatch.setattr(
        "rca.agents.run_critic",
        lambda **kw: CriticReview(round_index=kw["round_index"], continue_investigation=False, confidence_ceiling="medium"),  # type: ignore[arg-type]
    )
    monkeypatch.setenv("RCA_RESEARCH_ENABLED", "true")

    try:
        run_investigation_loop(
            city_id=0,
            dt="2024-05-16",
            signal_evidence={"signal_label": "drop"},
            memory_notes=[],
            run_id="test",
            settings=settings,
            logger=logger,
            client_factory=lambda n: None,
        )
    finally:
        os.environ.pop("RCA_RESEARCH_ENABLED", None)

    assert "news_agent" not in dispatched, "news_agent must not run in round 1"
    assert "statistician" in dispatched


def test_investigation_loop_memory_context_used_when_notes_present(monkeypatch: pytest.MonkeyPatch) -> None:
    """memory_context.used is True when memory_notes is non-empty."""
    from rca.agents import run_investigation_loop
    from rca.llm import LLMSettings
    from rca.runlog import RunLogger

    settings = LLMSettings(api_key="x", base_url="http://localhost", model="test", thinking_enabled=False)
    logger = RunLogger(run_id="test", city_id=0, dt="2024-05-16")

    monkeypatch.setattr(
        "rca.agents.plan_investigation",
        lambda **kw: PlannerDecision(selected_agents=["statistician"], rationale="", news_query="", objective=""),
    )
    monkeypatch.setattr(
        "rca.agents._run_agents_parallel",
        lambda **kw: [AgentRunResult(name="statistician", focus="f", memo_markdown="OK.", tool_calls=[])],
    )
    monkeypatch.setattr(
        "rca.agents.run_critic",
        lambda **kw: CriticReview(round_index=kw["round_index"], continue_investigation=False, confidence_ceiling="medium"),  # type: ignore[arg-type]
    )

    state = run_investigation_loop(
        city_id=0,
        dt="2024-05-16",
        signal_evidence={"signal_label": "drop"},
        memory_notes=[{"content": "Stockout was high last month."}],
        run_id="test",
        settings=settings,
        logger=logger,
        client_factory=lambda n: None,
    )

    assert state.memory_context.used is True
