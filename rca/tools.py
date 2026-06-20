"""Agent tool implementations — all reads from Supabase.

The signal frame is loaded once per process from rca_city_signal_v and cached.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any, Callable

import pandas as pd

from rca.config import (
    DEFAULT_DROP_THRESHOLD_PCT,
    DEFAULT_LIFT_THRESHOLD_PCT,
    make_supabase_client,
)
from rca.evidence import get_city_day_evidence
from rca.outcomes import get_prior_rca as load_prior_rca


ToolFunction = Callable[..., dict[str, Any]]


def _round_float(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return round(float(value), digits)


# ---------------------------------------------------------------------------
# Cached signal frame — loaded once from Supabase rca_city_signal_v
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _signal_frame() -> pd.DataFrame:
    """Load all city-days from the rca_city_signal_v view and cache."""
    client = make_supabase_client()
    resp = (
        client.table("rca_city_signal_v")
        .select(
            "city_id,dt,total_sales,weekday,density_tier,holiday_name_inferred,"
            "previous_day_sales,trailing_7d_avg_sales,same_weekday_4w_avg_sales,"
            "forecast_sales,day_over_day_pct_change,trailing_7d_pct_change,"
            "same_weekday_4w_pct_change,finance_forecast_pct_change,signal_label"
        )
        .limit(2000)
        .execute()
    )
    frame = pd.DataFrame(resp.data or [])
    if frame.empty:
        raise RuntimeError(
            "rca_city_signal_v returned no rows. "
            "Run 'rca build' to populate Supabase, then ensure migration 0009 has been applied."
        )
    frame["dt"] = pd.to_datetime(frame["dt"])
    frame["dt_label"] = frame["dt"].dt.strftime("%Y-%m-%d")
    return frame


def _get_signal_row(city_id: int, dt: str) -> pd.Series:
    frame = _signal_frame()
    matched = frame[(frame["city_id"] == city_id) & (frame["dt_label"] == dt)]
    if matched.empty:
        raise ValueError(f"No signal row found for city_id={city_id} dt={dt}")
    return matched.iloc[0]


def _get_history_slice(city_id: int, dt: str, days: int = 7) -> pd.DataFrame:
    frame = _signal_frame()
    city_frame = frame[frame["city_id"] == city_id].sort_values("dt").reset_index(drop=True)
    pos_mask = city_frame["dt_label"] == dt
    if not pos_mask.any():
        raise ValueError(f"No history row found for city_id={city_id} dt={dt}")
    pos = int(pos_mask.idxmax())
    start = max(0, pos - days)
    return city_frame.iloc[start : pos + 1].copy()


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def get_signal_evidence(city_id: int, dt: str) -> dict[str, Any]:
    row = _get_signal_row(city_id, dt)
    signal_label = str(row.get("signal_label", "neutral") or "neutral")
    return {
        "city_id": city_id,
        "dt": dt,
        "signal_label": signal_label,
        "current_sales": _round_float(row["total_sales"]),
        "forecast_sales": _round_float(row.get("forecast_sales")),
        "previous_day_sales": _round_float(row["previous_day_sales"]),
        "trailing_7d_avg_sales": _round_float(row["trailing_7d_avg_sales"]),
        "same_weekday_4w_avg_sales": _round_float(row["same_weekday_4w_avg_sales"]),
        "day_over_day_pct_change": _round_float(row["day_over_day_pct_change"]),
        "trailing_7d_pct_change": _round_float(row["trailing_7d_pct_change"]),
        "same_weekday_4w_pct_change": _round_float(row["same_weekday_4w_pct_change"]),
        "finance_forecast_pct_change": _round_float(row.get("finance_forecast_pct_change")),
        "thresholds": {
            "drop_lte_pct": DEFAULT_DROP_THRESHOLD_PCT,
            "lift_gte_pct": DEFAULT_LIFT_THRESHOLD_PCT,
        },
        "weekday": str(row["weekday"]),
        "holiday_name_inferred": str(row["holiday_name_inferred"] or ""),
    }


def get_intraday_profile(city_id: int, dt: str) -> dict[str, Any]:
    """Return the 24-hour intraday sales profile and deviation z-scores for one city-day."""
    client = make_supabase_client()
    resp = (
        client.table("rca_city_hourly")
        .select("hour, sales, sales_share, deviation_z, stockout_rate")
        .eq("city_id", city_id)
        .eq("dt", dt)
        .order("hour")
        .execute()
    )
    rows = resp.data or []

    if not rows:
        return {
            "city_id": city_id,
            "dt": dt,
            "available": False,
            "note": "No intraday profile. Run 'rca build' to regenerate analytics.",
        }

    hourly = [
        {
            "hour": int(r["hour"]),
            "sales": _round_float(r["sales"]),
            "sales_share_pct": round(float(r["sales_share"]) * 100, 2) if r["sales_share"] is not None else None,
            "deviation_z": _round_float(r["deviation_z"]),
            "stockout_rate": _round_float(r["stockout_rate"]),
        }
        for r in rows
    ]
    notable = sorted(hourly, key=lambda h: abs(h["deviation_z"] or 0), reverse=True)[:4]

    return {
        "city_id": city_id,
        "dt": dt,
        "available": True,
        "hourly": hourly,
        "notable_hours": notable,
    }


def get_sales_context(city_id: int, dt: str, history_days: int = 7) -> dict[str, Any]:
    signal_row = _get_signal_row(city_id, dt)
    history = _get_history_slice(city_id, dt, days=history_days)
    rows = [
        {
            "dt": row.dt_label,
            "total_sales": _round_float(row.total_sales),
            "weekday": str(row.weekday),
            "holiday_name_inferred": str(row.holiday_name_inferred or ""),
        }
        for row in history.itertuples(index=False)
    ]
    return {
        "city_id": city_id,
        "dt": dt,
        "history_window_days": history_days,
        "current_total_sales": _round_float(signal_row["total_sales"]),
        "history": rows,
        "sales_baselines": {
            "previous_day_sales": _round_float(signal_row["previous_day_sales"]),
            "trailing_7d_avg_sales": _round_float(signal_row["trailing_7d_avg_sales"]),
            "same_weekday_4w_avg_sales": _round_float(signal_row["same_weekday_4w_avg_sales"]),
            "forecast_sales": _round_float(signal_row.get("forecast_sales")),
        },
    }


def get_stockout_context(city_id: int, dt: str) -> dict[str, Any]:
    record = get_city_day_evidence(city_id, dt)
    history = _get_history_slice(city_id, dt, days=7)
    trailing_avg = (
        _round_float(history["total_sales"].iloc[:-1].mean()) if len(history) > 1 else None
    )
    return {
        "city_id": city_id,
        "dt": dt,
        "avg_stockout_hours": _round_float(record["stockout"]["avg_stockout_hours"]),
        "stockout_product_rate": _round_float(record["stockout"]["stockout_product_rate"]),
        "severe_stockout_product_rate": _round_float(record["stockout"]["severe_stockout_product_rate"]),
        "full_stockout_product_rate": _round_float(record["stockout"]["full_stockout_product_rate"]),
        "hourly_stockout_rate_peak": _round_float(max(record["stockout"]["hourly_stockout_rate"])),
        "current_total_sales": _round_float(record["sales"]["total_sales"]),
        "recent_avg_sales": trailing_avg,
    }


def get_stockout_baseline(city_id: int, dt: str, window: int = 30) -> dict[str, Any]:
    """Return this city's rolling stockout baseline for the N days before dt."""
    client = make_supabase_client()

    from datetime import datetime, timedelta
    dt_date = datetime.strptime(dt, "%Y-%m-%d").date()
    window_start = (dt_date - timedelta(days=window)).isoformat()

    resp = (
        client.table("rca_city_series")
        .select("dt, stockout_product_rate, severe_stockout_rate, full_stockout_product_rate, avg_stockout_hours")
        .eq("city_id", city_id)
        .lt("dt", dt)
        .gte("dt", window_start)
        .execute()
    )
    rows = resp.data or []

    if not rows:
        return {
            "city_id": city_id,
            "dt": dt,
            "window_days": window,
            "baseline_available": False,
            "note": "No prior stockout data in window.",
        }

    avg_so = sum(r["stockout_product_rate"] or 0 for r in rows) / len(rows)
    avg_severe = sum(r["severe_stockout_rate"] or 0 for r in rows) / len(rows)
    avg_full = sum(r["full_stockout_product_rate"] or 0 for r in rows) / len(rows)
    avg_hours = sum(r["avg_stockout_hours"] or 0 for r in rows) / len(rows)

    current = get_city_day_evidence(city_id, dt)
    cur_rate = current["stockout"]["stockout_product_rate"]
    ratio = _round_float(cur_rate / avg_so) if avg_so > 0 else None

    return {
        "city_id": city_id,
        "dt": dt,
        "window_days": len(rows),
        "baseline_available": True,
        "baseline": {
            "avg_stockout_product_rate": _round_float(avg_so),
            "avg_severe_stockout_product_rate": _round_float(avg_severe),
            "avg_full_stockout_product_rate": _round_float(avg_full),
            "avg_stockout_hours": _round_float(avg_hours),
        },
        "current_day": {
            "stockout_product_rate": _round_float(cur_rate),
            "severe_stockout_product_rate": _round_float(current["stockout"]["severe_stockout_product_rate"]),
            "avg_stockout_hours": _round_float(current["stockout"]["avg_stockout_hours"]),
        },
        "stockout_rate_vs_baseline": ratio,
        "interpretation": (
            f"Current stockout rate is {ratio:.1f}x the {len(rows)}-day baseline."
            if ratio is not None
            else "Cannot compute ratio — baseline is zero."
        ),
    }


def get_discount_context(city_id: int, dt: str) -> dict[str, Any]:
    record = get_city_day_evidence(city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "avg_discount": _round_float(record["discount"]["avg_discount"]),
        "discounted_product_rate": _round_float(record["discount"]["discounted_product_rate"]),
        "deep_discount_product_rate": _round_float(record["discount"]["deep_discount_product_rate"]),
    }


def get_activity_context(city_id: int, dt: str) -> dict[str, Any]:
    record = get_city_day_evidence(city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "activity_product_rate": _round_float(record["activity"]["activity_product_rate"]),
        "activity_sales_share": _round_float(record["activity"]["activity_sales_share"]),
    }


def get_calendar_weather_context(city_id: int, dt: str) -> dict[str, Any]:
    record = get_city_day_evidence(city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "weekday": record["holiday"]["weekday"],
        "is_weekend": record["holiday"]["is_weekend"],
        "holiday_name_inferred": record["holiday"]["holiday_name_inferred"],
        "holiday_flag": record["holiday"]["holiday_flag"],
        "precpt": _round_float(record["weather"]["precpt"]),
        "avg_temperature": _round_float(record["weather"]["avg_temperature"]),
        "avg_humidity": _round_float(record["weather"]["avg_humidity"]),
        "avg_wind_level": _round_float(record["weather"]["avg_wind_level"]),
    }


def get_peer_city_context(city_id: int, dt: str) -> dict[str, Any]:
    row = _get_signal_row(city_id, dt)
    frame = _signal_frame()
    daily = frame[frame["dt_label"] == str(row["dt_label"] if "dt_label" in row.index else dt)].copy()

    # Density tier from the cached signal frame
    density_tier = str(row.get("density_tier", "3") or "3")
    tier_daily = daily[daily["density_tier"] == density_tier]

    overall_avg = _round_float(daily["total_sales"].mean())
    tier_avg = _round_float(tier_daily["total_sales"].mean())

    rank = int(daily["total_sales"].rank(method="min", ascending=False)[daily["city_id"] == city_id].iloc[0])
    tier_rank = int(
        tier_daily["total_sales"].rank(method="min", ascending=False)[tier_daily["city_id"] == city_id].iloc[0]
        if not tier_daily[tier_daily["city_id"] == city_id].empty
        else 1
    )

    # Segment label for this city
    segment_label = _get_city_segment(city_id)

    return {
        "city_id": city_id,
        "dt": dt,
        "density_tier": density_tier,
        "segment_label": segment_label,
        "city_total_sales": _round_float(row["total_sales"]),
        "tier_avg_sales_same_day": tier_avg,
        "overall_avg_sales_same_day": overall_avg,
        "overall_rank_same_day": rank,
        "overall_city_count": int(daily.shape[0]),
        "tier_rank_same_day": tier_rank,
        "tier_city_count": int(tier_daily.shape[0]),
    }


@lru_cache(maxsize=18)
def _get_city_segment(city_id: int) -> str | None:
    """Fetch segment label for a city from rca_city_segment (cached per city)."""
    if not os.getenv("SUPABASE_URL"):
        return None
    try:
        client = make_supabase_client()
        resp = (
            client.table("rca_city_segment")
            .select("segment_label")
            .eq("city_id", city_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        return str(rows[0]["segment_label"]) if rows and rows[0].get("segment_label") else None
    except Exception:
        return None


def search_news(query: str, max_results: int = 5) -> dict[str, Any]:
    from duckduckgo_search import DDGS
    results = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
    except Exception as exc:
        return {"query": query, "error": str(exc), "results": []}
    return {"query": query, "result_count": len(results), "results": results}


def get_prior_rca(city_id: int) -> dict[str, Any]:
    return load_prior_rca(city_id)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_signal_evidence": {
        "description": "Get the precomputed city-day sales trigger signal and baseline comparisons.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_signal_evidence,
    },
    "get_sales_context": {
        "description": "Get current sales plus recent city sales history and baseline windows.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "history_days": {"type": "integer", "minimum": 3, "maximum": 14},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_sales_context,
    },
    "get_stockout_context": {
        "description": "Get stockout evidence for one city-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_stockout_context,
    },
    "get_stockout_baseline": {
        "description": (
            "Get this city's rolling stockout baseline for the N days before the trigger date. "
            "Returns the baseline average rates and the ratio of today's rate to the baseline."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "window": {
                    "type": "integer",
                    "minimum": 7,
                    "maximum": 60,
                    "default": 30,
                    "description": "Number of days before dt to average over.",
                },
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_stockout_baseline,
    },
    "get_discount_context": {
        "description": "Get discount evidence for one city-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_discount_context,
    },
    "get_activity_context": {
        "description": "Get promotional activity evidence for one city-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_activity_context,
    },
    "get_calendar_weather_context": {
        "description": "Get holiday, weekday, weekend, and weather context for one city-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_calendar_weather_context,
    },
    "get_peer_city_context": {
        "description": "Compare this city against same-day peers in its density tier group.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_peer_city_context,
    },
    "search_news": {
        "description": "Search the web for news or events relevant to a retail sales move.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "function": search_news,
    },
    "get_intraday_profile": {
        "description": (
            "Get the 24-hour hourly sales profile for one city-day, including deviation z-scores "
            "vs the city's typical hourly shape."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_intraday_profile,
    },
    "get_prior_rca": {
        "description": "Get prior RCA outcomes for this city from Supabase run history.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
            },
            "required": ["city_id"],
            "additionalProperties": False,
        },
        "function": get_prior_rca,
    },
}


def get_tool_schemas(tool_names: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    schemas: list[dict[str, Any]] = []
    names = list(tool_names) if tool_names is not None else list(TOOL_REGISTRY.keys())
    for name in names:
        tool = TOOL_REGISTRY[name]
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool["description"],
                    "parameters": tool["parameters"],
                },
            }
        )
    return schemas


def execute_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {name}"}
    function: ToolFunction = TOOL_REGISTRY[name]["function"]
    try:
        coerced = dict(arguments)
        if "city_id" in coerced:
            coerced["city_id"] = int(coerced["city_id"])
        return function(**coerced)
    except Exception as e:
        return {"error": str(e)}
