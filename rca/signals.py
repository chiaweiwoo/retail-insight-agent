"""Signal helpers for city/date expected-sales screening."""
from __future__ import annotations

from typing import Any

from rca.config import TABLE_SIGNALS, make_supabase_schema_client


def get_signal_row(city_id: int, dt: str) -> dict[str, Any]:
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_SIGNALS)
        .select("*")
        .eq("city_id", city_id)
        .eq("dt", dt)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise ValueError(f"No signal row found for city_id={city_id} dt={dt}")
    return rows[0]


def get_signal_dates_for_city(city_id: int) -> list[str]:
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_SIGNALS)
        .select("dt,signal_label")
        .eq("city_id", city_id)
        .in_("signal_label", ["drop", "lift"])
        .order("dt")
        .execute()
    )
    return [str(row["dt"]) for row in (result.data or [])]
