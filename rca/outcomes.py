from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rca.config import TABLE_COMPLETIONS, TABLE_OUTCOMES, current_timestamp_sgt_iso, make_supabase_schema_client


@dataclass
class OutcomeRecord:
    run_id: str
    city_id: int
    dt: str
    signal_label: str
    confidence: str
    headline: str
    # markdown columns (dashboard preview)
    decision_card_markdown: str = ""
    report_markdown: str = ""
    prediction_markdown: str = ""
    prescription_markdown: str = ""
    # workflow metadata
    status: str = "complete"
    round_count: int = 1
    # JSONB artifact columns — accept any JSON-serialisable dict/list
    decision_brief_json: dict[str, Any] = field(default_factory=dict)
    hypotheses_json: list[dict[str, Any]] = field(default_factory=list)
    evidence_ledger_json: list[dict[str, Any]] = field(default_factory=list)
    investigation_rounds_json: list[dict[str, Any]] = field(default_factory=list)
    critic_reviews_json: list[dict[str, Any]] = field(default_factory=list)
    monitoring_plan_json: dict[str, Any] = field(default_factory=dict)
    evaluation_json: dict[str, Any] = field(default_factory=dict)
    memory_context_json: dict[str, Any] = field(default_factory=dict)


def record_outcome(record: OutcomeRecord) -> None:
    client = make_supabase_schema_client()
    client.table(TABLE_OUTCOMES).upsert(
        {
            "run_id": record.run_id,
            "city_id": record.city_id,
            "dt": record.dt,
            "signal_label": record.signal_label,
            "confidence": record.confidence,
            "headline": record.headline,
            "status": record.status,
            "round_count": record.round_count,
            "generated_at": current_timestamp_sgt_iso(),
            "decision_card_markdown": record.decision_card_markdown,
            "report_markdown": record.report_markdown,
            "prediction_markdown": record.prediction_markdown,
            "prescription_markdown": record.prescription_markdown,
            "decision_brief_json": record.decision_brief_json,
            "hypotheses_json": record.hypotheses_json,
            "evidence_ledger_json": record.evidence_ledger_json,
            "investigation_rounds_json": record.investigation_rounds_json,
            "critic_reviews_json": record.critic_reviews_json,
            "monitoring_plan_json": record.monitoring_plan_json,
            "evaluation_json": record.evaluation_json,
            "memory_context_json": record.memory_context_json,
        },
        on_conflict="run_id",
    ).execute()


def get_prior_outcomes(city_id: int, limit: int = 5) -> list[dict[str, Any]]:
    """Return latest outcomes for a city ordered by generated_at descending."""
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_OUTCOMES)
        .select("run_id,dt,signal_label,confidence,headline,status,round_count,generated_at")
        .eq("city_id", city_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def get_latest_outcome_for_date(city_id: int, dt: str) -> dict[str, Any] | None:
    """Return the most recent outcome for a specific city/date (dashboard use)."""
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_OUTCOMES)
        .select("*")
        .eq("city_id", city_id)
        .eq("dt", dt)
        .order("generated_at", desc=True)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    return rows[0] if rows else None


def record_completion(
    *,
    run_id: str,
    city_id: int,
    dt: str,
    node_name: str,
    model: str,
    content: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    tool_calls_json: list[dict[str, Any]] | None = None,
) -> None:
    client = make_supabase_schema_client()
    try:
        client.table(TABLE_COMPLETIONS).insert(
            {
                "run_id": run_id,
                "city_id": city_id,
                "dt": dt,
                "ts": current_timestamp_sgt_iso(),
                "node_name": node_name,
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "content": content,
                "tool_calls_json": tool_calls_json or [],
            }
        ).execute()
    except Exception:
        return
