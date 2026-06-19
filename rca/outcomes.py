from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path
from typing import Any

import duckdb

from rca.config import LOG_DB_PATH


@dataclass(frozen=True)
class OutcomeRecord:
    run_name: str
    store_alias: str
    dt: str
    signal_label: str
    top_driver: str
    driver_class: str
    confidence: str
    escalated: bool
    brief_headline: str
    decision_card_markdown: str


def _resolve_db_path(db_path: Path | None) -> Path:
    return db_path or LOG_DB_PATH


def ensure_outcome_table(db_path: Path | None = None) -> None:
    db_path = _resolve_db_path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS rca_outcome (
                run_name TEXT NOT NULL,
                store_alias TEXT NOT NULL,
                dt TEXT NOT NULL,
                signal_label TEXT NOT NULL,
                top_driver TEXT NOT NULL,
                driver_class TEXT NOT NULL,
                confidence TEXT NOT NULL,
                escalated BOOLEAN NOT NULL,
                brief_headline TEXT NOT NULL,
                decision_card_markdown TEXT NOT NULL
            )
            """
        )
    finally:
        con.close()


def record_outcome(record: OutcomeRecord, db_path: Path | None = None) -> None:
    db_path = _resolve_db_path(db_path)
    ensure_outcome_table(db_path)
    con = duckdb.connect(str(db_path))
    try:
        con.execute(
            """
            INSERT INTO rca_outcome VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                record.run_name,
                record.store_alias,
                record.dt,
                record.signal_label,
                record.top_driver,
                record.driver_class,
                record.confidence,
                record.escalated,
                record.brief_headline,
                record.decision_card_markdown,
            ],
        )
    finally:
        con.close()


def get_prior_rca(
    store_alias: str,
    db_path: Path | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    db_path = _resolve_db_path(db_path)
    if not db_path.exists():
        return {
            "store_alias": store_alias,
            "previous_trigger_count": 0,
            "top_driver_counts": [],
            "recent_outcomes": [],
        }

    con = duckdb.connect(str(db_path), read_only=True)
    try:
        table_exists = con.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = 'main' AND table_name = 'rca_outcome'
            """
        ).fetchone()[0]
        if int(table_exists) == 0:
            return {
                "store_alias": store_alias,
                "previous_trigger_count": 0,
                "top_driver_counts": [],
                "recent_outcomes": [],
            }

        previous_trigger_count = int(
            con.execute(
                "SELECT COUNT(*) FROM rca_outcome WHERE store_alias = ?",
                [store_alias],
            ).fetchone()[0]
        )
        top_driver_rows = con.execute(
            """
            SELECT top_driver, COUNT(*) AS trigger_count
            FROM rca_outcome
            WHERE store_alias = ?
            GROUP BY top_driver
            ORDER BY trigger_count DESC, top_driver ASC
            LIMIT 3
            """,
            [store_alias],
        ).fetchall()
        recent_rows = con.execute(
            """
            SELECT dt, signal_label, top_driver, driver_class, confidence, escalated, brief_headline
            FROM rca_outcome
            WHERE store_alias = ?
            ORDER BY dt DESC
            LIMIT ?
            """,
            [store_alias, limit],
        ).fetchall()
    finally:
        con.close()

    return {
        "store_alias": store_alias,
        "previous_trigger_count": previous_trigger_count,
        "top_driver_counts": [
            {"top_driver": str(top_driver), "trigger_count": int(trigger_count)}
            for top_driver, trigger_count in top_driver_rows
        ],
        "recent_outcomes": [
            {
                "dt": str(dt),
                "signal_label": str(signal_label),
                "top_driver": str(top_driver),
                "driver_class": str(driver_class),
                "confidence": str(confidence),
                "escalated": bool(escalated),
                "brief_headline": str(brief_headline),
            }
            for dt, signal_label, top_driver, driver_class, confidence, escalated, brief_headline in recent_rows
        ],
    }


def build_outcome_record(
    *,
    run_name: str,
    store_alias: str,
    dt: str,
    signal_evidence: dict[str, Any],
    coordinator_report_markdown: str,
    decision_card_markdown: str,
) -> OutcomeRecord:
    return OutcomeRecord(
        run_name=run_name,
        store_alias=store_alias,
        dt=dt,
        signal_label=str(signal_evidence.get("signal_label", "unknown")),
        top_driver=_extract_top_driver(coordinator_report_markdown),
        driver_class=_extract_driver_class(coordinator_report_markdown),
        confidence=_extract_bullet_value(decision_card_markdown, "confidence") or "unknown",
        escalated=(_extract_bullet_value(decision_card_markdown, "escalate") or "").strip().lower() == "yes",
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
