"""City replay harness: reset state, rerun all signal dates, review output.

reset_city_state  - deletes all outputs + caches for a city (outcomes,
                    events, completions, memory, evidence_cache, external_events)
find_signal_dates - returns triggered city dates oldest to latest from rca.signals
replay_city       - orchestrates reset, rerun, review, store, and progress output
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from rca.config import (
    TABLE_COMPLETIONS,
    TABLE_EVENTS,
    TABLE_EVIDENCE_CACHE,
    TABLE_EXTERNAL_EVENTS,
    TABLE_MEMORY,
    TABLE_OUTCOMES,
    current_timestamp_sgt_label,
    make_supabase_schema_client,
)
from rca.graph import run_rca_graph
from rca.reviewer import ReplayReview, review_outcome, store_replay_review


# ── Summary type ──────────────────────────────────────────────────────────────


@dataclass
class ReplaySummary:
    batch_id: str
    city_id: int
    total_dates: int
    passed_count: int
    avg_eval_score: float
    avg_alignment_score: float | None
    top_cons: list[tuple[str, int]] = field(default_factory=list)


# ── Reset ─────────────────────────────────────────────────────────────────────


def reset_city_state(city_id: int) -> dict[str, int]:
    """Delete all outputs and caches for a city. Returns {table: rows_deleted}."""
    client = make_supabase_schema_client()
    tables = [
        TABLE_OUTCOMES,
        TABLE_EVENTS,
        TABLE_COMPLETIONS,
        TABLE_MEMORY,
        TABLE_EVIDENCE_CACHE,
        TABLE_EXTERNAL_EVENTS,
    ]
    counts: dict[str, int] = {}
    for table in tables:
        try:
            result = client.table(table).delete().eq("city_id", city_id).execute()
            counts[table] = len(result.data or [])
        except Exception:
            counts[table] = -1
    return counts


# ── Signal dates ──────────────────────────────────────────────────────────────


def find_signal_dates(city_id: int, limit: int | None = None) -> list[str]:
    """Return triggered (drop/lift) dates for the city, oldest first."""
    from rca.config import TABLE_SIGNALS

    client = make_supabase_schema_client()
    query = (
        client.table(TABLE_SIGNALS)
        .select("dt")
        .eq("city_id", city_id)
        .in_("signal_label", ["drop", "lift"])
        .order("dt")
    )
    if limit is not None:
        query = query.limit(limit)
    result = query.execute()
    return [str(row["dt"]) for row in (result.data or [])]


# ── Replay loop ───────────────────────────────────────────────────────────────


def replay_city(
    city_id: int,
    *,
    reset: bool = True,
    dry_run: bool = False,
    limit: int | None = None,
    review: bool = True,
    batch_id: str | None = None,
    settings: Any = None,
    client_factory: Any = None,
) -> ReplaySummary:
    """Run reset, rerun all signal dates, and optionally review one city.

    Memory accumulates across dates within the batch so the agent learns
    as it processes oldest to latest dates: the intended learning-mode replay.
    """
    from rca.stubclient import stub_client_factory

    effective_batch_id = batch_id or current_timestamp_sgt_label()
    effective_client_factory = stub_client_factory if dry_run else client_factory

    if reset:
        counts = reset_city_state(city_id)
        _print(f"Reset city {city_id}:")
        for table, n in counts.items():
            _print(f"  {table}: {n} rows deleted")

    dates = find_signal_dates(city_id, limit=limit)
    if not dates:
        _print(f"No triggered signal dates found for city {city_id}.")
        return ReplaySummary(
            batch_id=effective_batch_id,
            city_id=city_id,
            total_dates=0,
            passed_count=0,
            avg_eval_score=0.0,
            avg_alignment_score=None,
        )

    _print(f"\nBatch: {effective_batch_id}  |  City: {city_id}  |  Dates: {len(dates)}\n")

    eval_scores: list[float] = []
    alignment_scores: list[float] = []
    all_cons: list[str] = []
    passed_count = 0

    for dt in dates:
        try:
            result = run_rca_graph(
                city_id=city_id,
                dt=dt,
                settings=settings,
                client_factory=effective_client_factory,
            )
        except Exception as exc:
            _print(f"  {dt}  ERROR during run: {exc}")
            continue

        eval_score = float((result.get("evaluation") or {}).get("score") or 0.0)
        eval_passed = bool((result.get("evaluation") or {}).get("passed") or False)
        signal_label = str((result.get("signal_evidence") or {}).get("signal_label") or "")
        run_id = str(result.get("run_id") or "")
        eval_scores.append(eval_score)
        if eval_passed:
            passed_count += 1

        alignment_label = ""
        if review:
            try:
                rv = review_outcome(
                    decision_brief=result.get("decision_brief") or {},
                    evidence_ledger=result.get("evidence_ledger") or [],
                    decision_card_markdown=result.get("final_report") or "",
                    settings=_load_settings_if_needed(settings, dry_run),
                    client_factory=effective_client_factory,
                    run_id=run_id,
                )
                alignment_scores.append(rv.alignment_score)
                all_cons.extend(rv.cons)
                alignment_label = rv.alignment_label
                store_replay_review(
                    batch_id=effective_batch_id,
                    run_id=run_id,
                    city_id=city_id,
                    dt=dt,
                    signal_label=signal_label,
                    review=rv,
                )
            except Exception as exc:
                alignment_label = f"error:{exc}"

        _print(
            f"  {dt}  {signal_label:<6}  eval={eval_score:.2f}{' PASS' if eval_passed else ' FAIL'}"
            + (f"  {alignment_label}" if review else "")
        )

    avg_eval = sum(eval_scores) / len(eval_scores) if eval_scores else 0.0
    avg_align = sum(alignment_scores) / len(alignment_scores) if alignment_scores else None

    con_counts = Counter(all_cons).most_common(3)
    top_cons = [(text, count) for text, count in con_counts]

    summary = ReplaySummary(
        batch_id=effective_batch_id,
        city_id=city_id,
        total_dates=len(dates),
        passed_count=passed_count,
        avg_eval_score=round(avg_eval, 4),
        avg_alignment_score=round(avg_align, 4) if avg_align is not None else None,
        top_cons=top_cons,
    )
    _print_summary(summary)
    return summary


# Helpers


def _print(text: str) -> None:
    import sys

    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.flush()


def _print_summary(summary: ReplaySummary) -> None:
    _print(f"\n{'-' * 50}")
    _print(f"Batch summary - {summary.batch_id}")
    _print(f"  Dates:       {summary.total_dates} triggered")
    _print(f"  Passed:      {summary.passed_count} / {summary.total_dates}  (eval >= 0.5)")
    _print(f"  Avg eval:    {summary.avg_eval_score:.3f}")
    if summary.avg_alignment_score is not None:
        _print(f"  Avg align:   {summary.avg_alignment_score:.3f}")
    if summary.top_cons:
        _print("  Top cons:")
        for text, count in summary.top_cons:
            _print(f"    - {text}  ({count} date{'s' if count != 1 else ''})")
    _print(f"{'-' * 50}\n")


def _load_settings_if_needed(settings: Any, dry_run: bool) -> Any:
    """Return settings if provided; load from env if not (stub skips the key check)."""
    if settings is not None:
        return settings
    if dry_run:
        from rca.llm import LLMSettings

        return LLMSettings(api_key="stub", base_url="stub", model="stub", thinking_enabled=False)
    from rca.llm import load_llm_settings

    return load_llm_settings()
