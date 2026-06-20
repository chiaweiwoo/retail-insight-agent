"""Evidence fetcher — reads from Supabase rca_city_series + rca_city_hourly.

No local database dependency.
"""
from __future__ import annotations

from typing import Any

from rca.config import make_supabase_client


def _client() -> Any:
    return make_supabase_client()


def list_city_ids() -> list[str]:
    result = _client().table("rca_city_series").select("city_id").execute()
    ids = sorted({str(r["city_id"]) for r in (result.data or [])})
    return ids


def list_dates() -> list[str]:
    result = (
        _client()
        .table("rca_city_series")
        .select("dt")
        .order("dt")
        .execute()
    )
    dates = sorted({str(r["dt"]) for r in (result.data or [])})
    return dates


def get_city_day_evidence(city_id: int, dt: str) -> dict[str, Any]:
    """Fetch all evidence for one city-day from Supabase.

    Returns the same nested dict shape that the agent tools expect.
    """
    client = _client()

    # ── Main facts from rca_city_series ──────────────────────────────────────
    series_resp = (
        client.table("rca_city_series")
        .select(
            "city_id, dt, total_sales, product_count, active_product_count, avg_sales_per_product,"
            "avg_stockout_hours, stockout_product_rate, severe_stockout_rate,"
            "full_stockout_product_rate,"
            "avg_discount, discounted_product_rate, deep_discount_product_rate,"
            "activity_product_rate, activity_sales_share,"
            "weekday, is_weekend, holiday_flag, holiday_name_inferred, holiday_note,"
            "precpt, avg_temperature, avg_humidity, avg_wind_level"
        )
        .eq("city_id", city_id)
        .eq("dt", dt)
        .limit(1)
        .execute()
    )
    rows = series_resp.data or []
    if not rows:
        raise ValueError(f"No evidence found for city_id={city_id} dt={dt}")
    s = rows[0]

    # ── Hourly profile from rca_city_hourly ───────────────────────────────────
    hourly_resp = (
        client.table("rca_city_hourly")
        .select("hour, sales, stockout_rate")
        .eq("city_id", city_id)
        .eq("dt", dt)
        .order("hour")
        .execute()
    )
    hourly_rows = hourly_resp.data or []

    # Build 24-element arrays (zero-filled if data is missing)
    hourly_by_h = {r["hour"]: r for r in hourly_rows}
    hourly_sales = [float(hourly_by_h[h]["sales"] or 0) if h in hourly_by_h else 0.0 for h in range(24)]
    hourly_stockout = [float(hourly_by_h[h]["stockout_rate"] or 0) if h in hourly_by_h else 0.0 for h in range(24)]

    return {
        "city_id": str(s["city_id"]),
        "dt": str(s["dt"]),
        "sales": {
            "product_count": int(s["product_count"] or 0),
            "active_product_count": int(s["active_product_count"] or 0),
            "total_sales": float(s["total_sales"] or 0),
            "avg_sales_per_product": float(s["avg_sales_per_product"] or 0),
            "hourly_sales": hourly_sales,
        },
        "stockout": {
            "avg_stockout_hours": float(s["avg_stockout_hours"] or 0),
            "stockout_product_rate": float(s["stockout_product_rate"] or 0),
            "severe_stockout_product_rate": float(s["severe_stockout_rate"] or 0),
            "full_stockout_product_rate": float(s["full_stockout_product_rate"] or 0),
            "hourly_stockout_rate": hourly_stockout,
        },
        "discount": {
            "avg_discount": float(s["avg_discount"] or 0),
            "discounted_product_rate": float(s["discounted_product_rate"] or 0),
            "deep_discount_product_rate": float(s["deep_discount_product_rate"] or 0),
        },
        "activity": {
            "activity_product_rate": float(s["activity_product_rate"] or 0),
            "activity_sales_share": float(s["activity_sales_share"] or 0),
        },
        "holiday": {
            "weekday": str(s["weekday"] or ""),
            "is_weekend": bool(s["is_weekend"]),
            "holiday_flag": bool(s["holiday_flag"]),
            "holiday_name_inferred": str(s["holiday_name_inferred"] or "normal_weekday"),
            "holiday_note": str(s["holiday_note"] or ""),
        },
        "weather": {
            "precpt": float(s["precpt"] or 0),
            "avg_temperature": float(s["avg_temperature"] or 0),
            "avg_humidity": float(s["avg_humidity"] or 0),
            "avg_wind_level": float(s["avg_wind_level"] or 0),
        },
    }
