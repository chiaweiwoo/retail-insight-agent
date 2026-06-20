from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rca.config import TABLE_COMPLETIONS, TABLE_OUTCOMES, current_timestamp_sgt_iso, make_supabase_schema_client


@dataclass(frozen=True)
class OutcomeRecord:
    run_id: str
    city_id: int
    dt: str
    signal_label: str
    confidence: str
    headline: str
    decision_card_markdown: str
    report_markdown: str
    prediction_markdown: str
    prescription_markdown: str


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
            "decision_card_markdown": record.decision_card_markdown,
            "report_markdown": record.report_markdown,
            "prediction_markdown": record.prediction_markdown,
            "prescription_markdown": record.prescription_markdown,
            "generated_at": current_timestamp_sgt_iso(),
        },
        on_conflict="city_id,dt",
    ).execute()


def get_prior_outcomes(city_id: int, limit: int = 5) -> list[dict[str, Any]]:
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_OUTCOMES)
        .select("dt,signal_label,confidence,headline")
        .eq("city_id", city_id)
        .order("generated_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


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
