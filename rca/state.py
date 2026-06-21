"""Pydantic v2 models for the RCA investigation state machine.

These types travel through the bounded investigation loop and are serialised
to JSONB columns in rca.outcomes via .model_dump(mode="json").
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Vocabulary literals ───────────────────────────────────────────────────────

ConfidenceLevel = Literal["low", "medium", "high"]
HypothesisStatus = Literal["open", "supported", "weakened", "rejected", "unknown"]
EvidenceType = Literal["observation", "inference", "external", "memory", "statistical"]
ClaimType = Literal["observation", "inference", "recommendation", "unknown"]
UrgencyLevel = Literal["low", "medium", "high"]
GapType = Literal[
    "missing_internal_evidence",
    "missing_external_context",
    "weak_causal_link",
    "baseline_conflict",
    "scope_violation",
    "format_violation",
    "insufficient_business_action",
    "unavailable_data",
]
GapSeverity = Literal["low", "medium", "high"]


# ── Core evidence/claim/hypothesis types ─────────────────────────────────────


class EvidenceItem(BaseModel):
    id: str
    source: str
    tool_name: str | None = None
    agent_name: str | None = None
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    supports: list[str] = Field(default_factory=list)
    weakens: list[str] = Field(default_factory=list)
    evidence_type: EvidenceType = "observation"


class Claim(BaseModel):
    id: str
    text: str
    claim_type: ClaimType = "observation"
    confidence: ConfidenceLevel = "low"
    evidence_ids: list[str] = Field(default_factory=list)
    caveat: str = ""


class Hypothesis(BaseModel):
    id: str
    title: str
    explanation: str
    status: HypothesisStatus = "open"
    confidence: ConfidenceLevel = "low"
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)


# ── Critic review types ───────────────────────────────────────────────────────


class CriticGap(BaseModel):
    id: str
    description: str
    severity: GapSeverity = "medium"
    gap_type: GapType = "missing_internal_evidence"
    suggested_agents: list[str] = Field(default_factory=list)
    suggested_tools: list[str] = Field(default_factory=list)


class CriticReview(BaseModel):
    round_index: int
    continue_investigation: bool
    confidence_ceiling: ConfidenceLevel
    gaps: list[CriticGap] = Field(default_factory=list)
    recommended_agents: list[str] = Field(default_factory=list)
    recommended_tools: list[str] = Field(default_factory=list)
    stop_reason: str = ""


# ── Investigation round ───────────────────────────────────────────────────────


class InvestigationRound(BaseModel):
    round_index: int
    objective: str
    selected_agents: list[str] = Field(default_factory=list)
    completed_agents: list[str] = Field(default_factory=list)
    new_evidence_ids: list[str] = Field(default_factory=list)
    new_claim_ids: list[str] = Field(default_factory=list)
    critic_review: CriticReview | None = None


# ── Decision output types ─────────────────────────────────────────────────────


class MonitoringPlan(BaseModel):
    metrics_to_watch: list[str] = Field(default_factory=list)
    review_horizon: str = ""
    escalation_trigger: str = ""


class DecisionBrief(BaseModel):
    headline: str
    confidence: ConfidenceLevel
    situation: str
    business_impact: str
    most_likely_explanation: str
    evidence_summary: list[str] = Field(default_factory=list)
    recommended_action: str
    alternatives: list[str] = Field(default_factory=list)
    owner_function: str
    urgency: UrgencyLevel
    expected_benefit: str
    monitoring_plan: MonitoringPlan = Field(default_factory=MonitoringPlan)
    unknowns: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)


# ── Evaluation types ──────────────────────────────────────────────────────────


class DeterministicCheck(BaseModel):
    name: str
    passed: bool
    severity: GapSeverity = "medium"
    message: str = ""


class LlmJudgeResult(BaseModel):
    enabled: bool = False
    groundedness: float | None = None
    calibration: float | None = None
    actionability: float | None = None
    management_usefulness: float | None = None
    scope_discipline: float | None = None
    restraint: float | None = None
    comment: str = ""


class EvaluationResult(BaseModel):
    passed: bool
    score: float
    deterministic_checks: list[DeterministicCheck] = Field(default_factory=list)
    llm_judge: LlmJudgeResult = Field(default_factory=LlmJudgeResult)


# ── Memory influence ──────────────────────────────────────────────────────────


class MemoryInfluence(BaseModel):
    used: bool
    memory_ids: list[int] = Field(default_factory=list)
    effect: str = ""


# ── Top-level run state ───────────────────────────────────────────────────────


class RcaRunState(BaseModel):
    run_id: str
    city_id: int
    dt: str
    signal_label: str = "neutral"

    hypotheses: list[Hypothesis] = Field(default_factory=list)
    evidence_ledger: list[EvidenceItem] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    investigation_rounds: list[InvestigationRound] = Field(default_factory=list)
    critic_reviews: list[CriticReview] = Field(default_factory=list)

    decision_brief: DecisionBrief | None = None
    monitoring_plan: MonitoringPlan = Field(default_factory=MonitoringPlan)
    evaluation: EvaluationResult | None = None
    memory_context: MemoryInfluence = Field(default_factory=lambda: MemoryInfluence(used=False))

    # Counters for deterministic ID generation within one run
    _ev_counter: int = 0
    _cl_counter: int = 0
    _hyp_counter: int = 0

    model_config = {"populate_by_name": True}

    def next_evidence_id(self) -> str:
        self._ev_counter += 1
        return f"ev_{self._ev_counter:03d}"

    def next_claim_id(self) -> str:
        self._cl_counter += 1
        return f"cl_{self._cl_counter:03d}"

    def next_hypothesis_id(self) -> str:
        self._hyp_counter += 1
        return f"hyp_{self._hyp_counter:03d}"
