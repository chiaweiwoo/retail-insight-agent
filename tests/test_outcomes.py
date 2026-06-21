from __future__ import annotations

import pytest

from rca.outcomes import OutcomeRecord
from rca.state import (
    Claim,
    CriticGap,
    CriticReview,
    DecisionBrief,
    EvaluationResult,
    EvidenceItem,
    Hypothesis,
    InvestigationRound,
    MemoryInfluence,
    MonitoringPlan,
    RcaRunState,
)


# ── OutcomeRecord ─────────────────────────────────────────────────────────────


def test_outcome_record_defaults_are_json_safe() -> None:
    import json

    record = OutcomeRecord(
        run_id="0_2024-06-09",
        city_id=0,
        dt="2024-06-09",
        signal_label="drop",
        confidence="medium",
        headline="Sales dropped 18% vs same-weekday baseline.",
    )
    payload = {
        "decision_brief_json": record.decision_brief_json,
        "hypotheses_json": record.hypotheses_json,
        "evidence_ledger_json": record.evidence_ledger_json,
        "investigation_rounds_json": record.investigation_rounds_json,
        "critic_reviews_json": record.critic_reviews_json,
        "monitoring_plan_json": record.monitoring_plan_json,
        "evaluation_json": record.evaluation_json,
        "memory_context_json": record.memory_context_json,
    }
    # Must not raise
    serialised = json.dumps(payload)
    assert isinstance(serialised, str)


def test_outcome_record_status_and_round_count_defaults() -> None:
    record = OutcomeRecord(
        run_id="0_2024-06-09",
        city_id=0,
        dt="2024-06-09",
        signal_label="drop",
        confidence="medium",
        headline="test",
    )
    assert record.status == "complete"
    assert record.round_count == 1


# ── Pydantic state models ─────────────────────────────────────────────────────


def test_hypothesis_rejects_invalid_status() -> None:
    with pytest.raises(Exception):
        Hypothesis(id="hyp_001", title="t", explanation="e", status="invalid")  # type: ignore[arg-type]


def test_hypothesis_rejects_invalid_confidence() -> None:
    with pytest.raises(Exception):
        Hypothesis(id="hyp_001", title="t", explanation="e", confidence="very_high")  # type: ignore[arg-type]


def test_evidence_item_rejects_invalid_type() -> None:
    with pytest.raises(Exception):
        EvidenceItem(id="ev_001", source="tool", summary="s", evidence_type="rumor")  # type: ignore[arg-type]


def test_claim_rejects_invalid_claim_type() -> None:
    with pytest.raises(Exception):
        Claim(id="cl_001", text="t", claim_type="speculation")  # type: ignore[arg-type]


def test_critic_review_rejects_invalid_confidence_ceiling() -> None:
    with pytest.raises(Exception):
        CriticReview(
            round_index=1,
            continue_investigation=False,
            confidence_ceiling="very_low",  # type: ignore[arg-type]
        )


# ── Pydantic model serialisation ──────────────────────────────────────────────


def test_evidence_item_serialises_to_json_compatible_dict() -> None:
    item = EvidenceItem(
        id="ev_001",
        source="get_inventory_context",
        tool_name="get_inventory_context",
        agent_name="inventory_agent",
        summary="Stockout rate was 35% on this date.",
        payload={"stockout_product_rate": 0.35},
        supports=["hyp_001"],
        evidence_type="observation",
    )
    d = item.model_dump(mode="json")
    assert d["id"] == "ev_001"
    assert d["evidence_type"] == "observation"
    assert isinstance(d["payload"], dict)


def test_investigation_round_serialises_correctly() -> None:
    gap = CriticGap(
        id="gap_001",
        description="Inventory explanation unverified.",
        severity="medium",
        gap_type="missing_internal_evidence",
        suggested_agents=["inventory_agent"],
    )
    review = CriticReview(
        round_index=1,
        continue_investigation=True,
        confidence_ceiling="medium",
        gaps=[gap],
        recommended_agents=["inventory_agent"],
        stop_reason="",
    )
    round_ = InvestigationRound(
        round_index=1,
        objective="Validate drop signal and check internal drivers.",
        selected_agents=["statistician", "sales_agent"],
        completed_agents=["statistician", "sales_agent"],
        new_evidence_ids=["ev_001", "ev_002"],
        critic_review=review,
    )
    d = round_.model_dump(mode="json")
    assert d["round_index"] == 1
    assert d["critic_review"]["continue_investigation"] is True
    assert d["critic_review"]["gaps"][0]["gap_type"] == "missing_internal_evidence"


def test_decision_brief_serialises_monitoring_plan() -> None:
    plan = MonitoringPlan(
        metrics_to_watch=["stockout_product_rate", "total_sales"],
        review_horizon="7 days",
        escalation_trigger="stockout_product_rate > 0.4",
    )
    brief = DecisionBrief(
        headline="Sales drop driven by inventory pressure.",
        confidence="medium",
        situation="City 0 recorded a 20% drop vs same-weekday baseline.",
        business_impact="Normalized sales below baseline by 20 units equivalent.",
        most_likely_explanation="Stockout pressure during peak hours reduced available SKUs.",
        recommended_action="Review replenishment schedule for peak SKUs.",
        owner_function="Inventory Planning",
        urgency="medium",
        expected_benefit="Reduce recurrence risk in next 7 days.",
        monitoring_plan=plan,
        unknowns=["Margin impact unknown — no cost data available."],
    )
    d = brief.model_dump(mode="json")
    assert d["confidence"] == "medium"
    assert d["monitoring_plan"]["metrics_to_watch"] == ["stockout_product_rate", "total_sales"]


def test_evaluation_result_score_is_float() -> None:
    result = EvaluationResult(passed=True, score=0.86)
    d = result.model_dump(mode="json")
    assert isinstance(d["score"], float)
    assert d["passed"] is True


def test_memory_influence_used_false() -> None:
    influence = MemoryInfluence(used=False, memory_ids=[], effect="No relevant memory found.")
    d = influence.model_dump(mode="json")
    assert d["used"] is False


def test_rca_run_state_id_counters_are_deterministic() -> None:
    state = RcaRunState(run_id="0_2024-06-09", city_id=0, dt="2024-06-09")
    assert state.next_evidence_id() == "ev_001"
    assert state.next_evidence_id() == "ev_002"
    assert state.next_claim_id() == "cl_001"
    assert state.next_hypothesis_id() == "hyp_001"


def test_rca_run_state_serialises_empty_state() -> None:
    import json

    state = RcaRunState(run_id="0_2024-06-09", city_id=0, dt="2024-06-09")
    d = state.model_dump(mode="json")
    serialised = json.dumps(d)
    assert "evidence_ledger" in serialised
    assert "hypotheses" in serialised
