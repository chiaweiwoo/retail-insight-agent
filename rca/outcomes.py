from __future__ import annotations

from dataclasses import dataclass
import os
import re
from pathlib import Path
from typing import Any

from rca.config import make_supabase_client


@dataclass(frozen=True)
class OutcomeRecord:
    run_name: str
    city_id: int
    dt: str
    signal_label: str
    top_driver: str
    driver_class: str
    confidence: str
    escalated: bool
    brief_headline: str
    decision_card_markdown: str


def record_outcome(record: OutcomeRecord, dry_run: bool = False) -> None:
    """Upsert a run outcome to Supabase rca_outcome. No-ops on dry-run."""
    if dry_run or not os.getenv("SUPABASE_URL"):
        return

    client = make_supabase_client()
    client.table("rca_outcome").upsert(
        {
            "run_name": record.run_name,
            "city_id": record.city_id,
            "dt": record.dt,
            "signal_label": record.signal_label,
            "top_driver": record.top_driver,
            "driver_class": record.driver_class,
            "confidence": record.confidence,
            "escalated": record.escalated,
            "brief_headline": record.brief_headline,
            "decision_card_markdown": record.decision_card_markdown,
        },
        on_conflict="run_name",
    ).execute()


def get_prior_rca(
    city_id: int,
    limit: int = 5,
) -> dict[str, Any]:
    """Read prior RCA outcomes for a store from Supabase."""
    if not os.getenv("SUPABASE_URL"):
        return _empty_prior(city_id)

    try:
        client = make_supabase_client()
        rows = (
            client
            .table("rca_outcome")
            .select("dt,signal_label,top_driver,driver_class,confidence,escalated,brief_headline")
            .eq("city_id", city_id)
            .order("dt", desc=True)
            .limit(limit)
            .execute()
        )
        data = rows.data or []
    except Exception:
        return _empty_prior(city_id)

    # Aggregate top drivers
    driver_counts: dict[str, int] = {}
    for row in data:
        d = str(row.get("top_driver", "unknown"))
        driver_counts[d] = driver_counts.get(d, 0) + 1

    return {
        "city_id": city_id,
        "previous_trigger_count": len(data),
        "top_driver_counts": [
            {"top_driver": d, "trigger_count": c}
            for d, c in sorted(driver_counts.items(), key=lambda x: -x[1])[:3]
        ],
        "recent_outcomes": [
            {
                "dt": str(row.get("dt")),
                "signal_label": str(row.get("signal_label")),
                "top_driver": str(row.get("top_driver")),
                "driver_class": str(row.get("driver_class")),
                "confidence": str(row.get("confidence")),
                "escalated": bool(row.get("escalated")),
                "brief_headline": str(row.get("brief_headline")),
            }
            for row in data
        ],
    }


def _empty_prior(city_id: int) -> dict[str, Any]:
    return {
        "city_id": city_id,
        "previous_trigger_count": 0,
        "top_driver_counts": [],
        "recent_outcomes": [],
    }


def build_outcome_record(
    *,
    run_name: str,
    city_id: int,
    dt: str,
    signal_evidence: dict[str, Any],
    coordinator_report_markdown: str,
    decision_card_markdown: str,
) -> OutcomeRecord:
    return OutcomeRecord(
        run_name=run_name,
        city_id=city_id,
        dt=dt,
        signal_label=str(signal_evidence.get("signal_label", "unknown")),
        top_driver=_extract_top_driver(coordinator_report_markdown),
        driver_class=_extract_driver_class(coordinator_report_markdown),
        confidence=_extract_bullet_value(decision_card_markdown, "confidence") or "unknown",
        escalated=(
            (_extract_bullet_value(decision_card_markdown, "escalate") or "").strip().lower()
            == "yes"
        ),
        brief_headline=_extract_bullet_value(decision_card_markdown, "headline") or "",
        decision_card_markdown=decision_card_markdown,
    )


def _extract_top_driver(report_markdown: str) -> str:
    match = re.search(r"## Likely Drivers\s+1\.\s+(.*)", report_markdown, re.DOTALL)
    if not match:
        return "unknown"
    first_line = match.group(1).splitlines()[0].strip()
    if "]" in first_line:
        first_line = first_line.split("]", 1)[1].strip()
    return first_line or "unknown"


def _extract_driver_class(report_markdown: str) -> str:
    match = re.search(r"\[([a-z_]+)\s*/\s*(high|medium|low)\]", report_markdown, re.IGNORECASE)
    if not match:
        return "unknown"
    return match.group(1).lower()


def _extract_bullet_value(markdown: str, field_name: str) -> str | None:
    match = re.search(rf"^- {re.escape(field_name)}:\s*(.+)$", markdown, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip()
