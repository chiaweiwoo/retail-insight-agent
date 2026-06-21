"""Runtime evidence tools backed by Supabase city/date facts."""
from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Callable

import pandas as pd

from rca.config import (
    DEFAULT_DROP_THRESHOLD_PCT,
    DEFAULT_LIFT_THRESHOLD_PCT,
    DEFAULT_NEWS_RESULTS,
    TABLE_CALENDAR,
    TABLE_GOALS,
    TABLE_INVENTORY,
    TABLE_PRICING,
    TABLE_PROMOTIONS,
    TABLE_SALES,
    TABLE_SIGNALS,
    TABLE_WEATHER,
    make_supabase_schema_client,
)
from rca.memory import (
    cache_external_events,
    get_cached_evidence,
    get_cached_external_events,
    get_memory_notes,
    put_cached_evidence,
)
from rca.outcomes import get_prior_outcomes


ToolFunction = Callable[..., dict[str, Any]]


def _round_float(value: float | None, digits: int = 4) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return round(float(value), digits)


def _client():
    return make_supabase_schema_client()


def _fetch_one(table: str, city_id: int, dt: str, columns: str = "*") -> dict[str, Any]:
    result = (
        _client()
        .table(table)
        .select(columns)
        .eq("city_id", city_id)
        .eq("dt", dt)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        raise ValueError(f"No row found in {table} for city_id={city_id} dt={dt}")
    return rows[0]


def _fetch_city_history(table: str, city_id: int, dt: str, columns: str = "*", limit: int = 90) -> list[dict[str, Any]]:
    result = (
        _client()
        .table(table)
        .select(columns)
        .eq("city_id", city_id)
        .lte("dt", dt)
        .order("dt", desc=True)
        .limit(limit)
        .execute()
    )
    rows = result.data or []
    return list(reversed(rows))


def get_signal_evidence(city_id: int, dt: str) -> dict[str, Any]:
    signal = _fetch_one(TABLE_SIGNALS, city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "signal_label": str(signal["signal_label"]),
        "current_sales": _round_float(signal.get("total_sales")),
        "expected_sales": _round_float(signal.get("expected_sales")),
        "deviation_pct": _round_float(signal.get("deviation_pct")),
        "goal_method": str(signal.get("goal_method") or ""),
        "weekday": str(signal.get("weekday") or ""),
        "holiday_name_inferred": str(signal.get("holiday_name_inferred") or ""),
        "thresholds": {
            "drop_lte_pct": DEFAULT_DROP_THRESHOLD_PCT,
            "lift_gte_pct": DEFAULT_LIFT_THRESHOLD_PCT,
        },
    }


def get_sales_context(city_id: int, dt: str, history_days: int = 14) -> dict[str, Any]:
    rows = _fetch_city_history(
        TABLE_SALES,
        city_id,
        dt,
        columns="dt,total_sales,store_count,product_count,active_product_count,avg_sales_per_product",
        limit=max(14, history_days + 2),
    )
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"No sales history found for city_id={city_id}")
    frame["dt"] = pd.to_datetime(frame["dt"])
    frame = frame.sort_values("dt").reset_index(drop=True)
    frame["dt_label"] = frame["dt"].dt.strftime("%Y-%m-%d")
    current = frame[frame["dt_label"] == dt]
    if current.empty:
        raise ValueError(f"No sales row found for city_id={city_id} dt={dt}")
    current_row = current.iloc[0]
    pos = int(current.index[0])
    history = frame.iloc[max(0, pos - history_days) : pos + 1]
    return {
        "city_id": city_id,
        "dt": dt,
        "current_total_sales": _round_float(current_row["total_sales"]),
        "store_count": int(current_row["store_count"]),
        "product_count": int(current_row["product_count"]),
        "active_product_count": int(current_row["active_product_count"]),
        "avg_sales_per_product": _round_float(current_row["avg_sales_per_product"]),
        "history": [
            {
                "dt": row.dt_label,
                "total_sales": _round_float(row.total_sales),
            }
            for row in history.itertuples(index=False)
        ],
    }


def get_inventory_context(city_id: int, dt: str) -> dict[str, Any]:
    row = _fetch_one(TABLE_INVENTORY, city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "avg_stockout_hours": _round_float(row.get("avg_stockout_hours")),
        "stockout_product_count": int(row.get("stockout_product_count") or 0),
        "stockout_product_rate": _round_float(row.get("stockout_product_rate")),
        "severe_stockout_product_count": int(row.get("severe_stockout_product_count") or 0),
        "severe_stockout_product_rate": _round_float(row.get("severe_stockout_product_rate")),
        "full_stockout_product_count": int(row.get("full_stockout_product_count") or 0),
        "full_stockout_product_rate": _round_float(row.get("full_stockout_product_rate")),
        "hourly_stockout_rate": [
            _round_float(row.get(f"hour_{hour:02d}_stockout_rate"))
            for hour in range(24)
        ],
    }


def get_pricing_context(city_id: int, dt: str) -> dict[str, Any]:
    row = _fetch_one(TABLE_PRICING, city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "avg_discount": _round_float(row.get("avg_discount")),
        "min_discount": _round_float(row.get("min_discount")),
        "discounted_product_count": int(row.get("discounted_product_count") or 0),
        "discounted_product_rate": _round_float(row.get("discounted_product_rate")),
        "deep_discounted_product_count": int(row.get("deep_discounted_product_count") or 0),
        "deep_discounted_product_rate": _round_float(row.get("deep_discounted_product_rate")),
    }


def get_promotions_context(city_id: int, dt: str) -> dict[str, Any]:
    row = _fetch_one(TABLE_PROMOTIONS, city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "activity_product_count": int(row.get("activity_product_count") or 0),
        "activity_product_rate": _round_float(row.get("activity_product_rate")),
        "activity_sales": _round_float(row.get("activity_sales")),
        "activity_sales_share": _round_float(row.get("activity_sales_share")),
        "caveat": "activity_flag is unlabeled and should be treated as an unknown internal activity indicator.",
    }


def get_calendar_weather_context(city_id: int, dt: str) -> dict[str, Any]:
    calendar = _fetch_one(TABLE_CALENDAR, city_id, dt)
    weather = _fetch_one(TABLE_WEATHER, city_id, dt)
    return {
        "city_id": city_id,
        "dt": dt,
        "weekday": str(calendar.get("weekday") or ""),
        "is_weekend": bool(calendar.get("is_weekend")),
        "holiday_flag": bool(calendar.get("holiday_flag")),
        "holiday_name_inferred": str(calendar.get("holiday_name_inferred") or ""),
        "holiday_caveat": "holiday names are inferred from date context, not source-labeled.",
        "precpt": _round_float(weather.get("precpt")),
        "avg_temperature": _round_float(weather.get("avg_temperature")),
        "avg_humidity": _round_float(weather.get("avg_humidity")),
        "avg_wind_level": _round_float(weather.get("avg_wind_level")),
    }


def get_intraday_profile(city_id: int, dt: str) -> dict[str, Any]:
    sales = _fetch_one(TABLE_SALES, city_id, dt)
    inventory = _fetch_one(TABLE_INVENTORY, city_id, dt)
    hourly = []
    total_sales = float(sales.get("total_sales") or 0.0)
    for hour in range(24):
        sales_value = float(sales.get(f"hour_{hour:02d}_sales") or 0.0)
        share = sales_value / total_sales if total_sales > 0 else 0.0
        hourly.append(
            {
                "hour": hour,
                "sales": _round_float(sales_value),
                "sales_share_pct": _round_float(share * 100.0, digits=2),
                "stockout_rate": _round_float(inventory.get(f"hour_{hour:02d}_stockout_rate")),
            }
        )
    return {"city_id": city_id, "dt": dt, "hourly": hourly}


def compare_recent_baseline(city_id: int, dt: str, window: int = 7) -> dict[str, Any]:
    cached = get_cached_evidence("compare_recent_baseline", {"city_id": city_id, "dt": dt, "window": window})
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    rows = _fetch_city_history(TABLE_SALES, city_id, dt, columns="dt,total_sales", limit=60)
    frame = pd.DataFrame(rows)
    frame["dt"] = pd.to_datetime(frame["dt"])
    frame = frame.sort_values("dt").reset_index(drop=True)
    frame["dt_label"] = frame["dt"].dt.strftime("%Y-%m-%d")
    current = frame[frame["dt_label"] == dt]
    if current.empty:
        raise ValueError(f"No sales row found for city_id={city_id} dt={dt}")
    pos = int(current.index[0])
    lookback = frame.iloc[max(0, pos - window) : pos]
    baseline = float(lookback["total_sales"].mean()) if not lookback.empty else None
    current_sales = float(current.iloc[0]["total_sales"])
    delta_pct = ((current_sales - baseline) / baseline * 100.0) if baseline and baseline > 0 else None
    result = {
        "city_id": city_id,
        "dt": dt,
        "window": window,
        "current_sales": _round_float(current_sales),
        "baseline_sales": _round_float(baseline),
        "delta_pct": _round_float(delta_pct),
        "cache_hit": False,
    }
    put_cached_evidence("compare_recent_baseline", {"city_id": city_id, "dt": dt, "window": window}, result)
    return result


def compare_same_weekday_baseline(city_id: int, dt: str, weeks: int = 4) -> dict[str, Any]:
    cached = get_cached_evidence("compare_same_weekday_baseline", {"city_id": city_id, "dt": dt, "weeks": weeks})
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    rows = _fetch_city_history(TABLE_SALES, city_id, dt, columns="dt,total_sales", limit=90)
    frame = pd.DataFrame(rows)
    frame["dt"] = pd.to_datetime(frame["dt"])
    frame = frame.sort_values("dt").reset_index(drop=True)
    frame["dt_label"] = frame["dt"].dt.strftime("%Y-%m-%d")
    frame["dow"] = frame["dt"].dt.dayofweek
    current = frame[frame["dt_label"] == dt]
    if current.empty:
        raise ValueError(f"No sales row found for city_id={city_id} dt={dt}")
    current_row = current.iloc[0]
    lookback = frame[(frame["dt"] < current_row["dt"]) & (frame["dow"] == current_row["dow"])].tail(weeks)
    baseline = float(lookback["total_sales"].mean()) if not lookback.empty else None
    current_sales = float(current_row["total_sales"])
    delta_pct = ((current_sales - baseline) / baseline * 100.0) if baseline and baseline > 0 else None
    result = {
        "city_id": city_id,
        "dt": dt,
        "weeks": weeks,
        "current_sales": _round_float(current_sales),
        "baseline_sales": _round_float(baseline),
        "delta_pct": _round_float(delta_pct),
        "cache_hit": False,
    }
    put_cached_evidence("compare_same_weekday_baseline", {"city_id": city_id, "dt": dt, "weeks": weeks}, result)
    return result


def detect_intraday_shift(city_id: int, dt: str, lookback_days: int = 7) -> dict[str, Any]:
    cached = get_cached_evidence("detect_intraday_shift", {"city_id": city_id, "dt": dt, "lookback_days": lookback_days})
    if cached is not None:
        cached["cache_hit"] = True
        return cached

    rows = _fetch_city_history(TABLE_SALES, city_id, dt, columns="*", limit=60)
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise ValueError(f"No sales history found for city_id={city_id}")
    frame["dt"] = pd.to_datetime(frame["dt"])
    frame = frame.sort_values("dt").reset_index(drop=True)
    frame["dt_label"] = frame["dt"].dt.strftime("%Y-%m-%d")
    current = frame[frame["dt_label"] == dt]
    if current.empty:
        raise ValueError(f"No sales row found for city_id={city_id} dt={dt}")
    pos = int(current.index[0])
    history = frame.iloc[max(0, pos - lookback_days) : pos]
    current_row = current.iloc[0]

    def shares(row: pd.Series) -> list[float]:
        total = float(row["total_sales"] or 0.0)
        if total <= 0:
            return [0.0] * 24
        return [float(row[f"hour_{hour:02d}_sales"] or 0.0) / total for hour in range(24)]

    current_shares = shares(current_row)
    if history.empty:
        baseline = [0.0] * 24
    else:
        baseline = list(pd.DataFrame([shares(row) for _, row in history.iterrows()]).mean())

    deviations = [
        {
            "hour": hour,
            "current_share_pct": _round_float(current_shares[hour] * 100.0, digits=2),
            "baseline_share_pct": _round_float(baseline[hour] * 100.0, digits=2),
            "delta_share_pct": _round_float((current_shares[hour] - baseline[hour]) * 100.0, digits=2),
        }
        for hour in range(24)
    ]
    notable_hours = sorted(deviations, key=lambda item: abs(item["delta_share_pct"] or 0.0), reverse=True)[:4]
    result = {
        "city_id": city_id,
        "dt": dt,
        "lookback_days": lookback_days,
        "notable_hours": notable_hours,
        "cache_hit": False,
    }
    put_cached_evidence("detect_intraday_shift", {"city_id": city_id, "dt": dt, "lookback_days": lookback_days}, result)
    return result


def get_memory_context(city_id: int, limit: int = 5) -> dict[str, Any]:
    return {
        "city_id": city_id,
        "recent_memories": get_memory_notes(city_id, limit=limit),
        "recent_outcomes": get_prior_outcomes(city_id, limit=limit),
    }


def search_external_events(city_id: int, dt: str, query: str, max_results: int = DEFAULT_NEWS_RESULTS) -> dict[str, Any]:
    cached = get_cached_external_events(city_id, dt, query)
    if cached:
        return {
            "city_id": city_id,
            "dt": dt,
            "query": query,
            "results": [
                row.get("result_json") or {
                    "source": row.get("source"),
                    "title": row.get("title"),
                    "url": row.get("url"),
                    "snippet": row.get("snippet"),
                    "published_at": row.get("published_at"),
                }
                for row in cached
            ],
            "cache_hit": True,
        }

    from duckduckgo_search import DDGS

    results = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            results.append(
                {
                    "source": "duckduckgo",
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "published_at": item.get("date"),
                }
            )
    cache_external_events(city_id, dt, query, results)
    return {"city_id": city_id, "dt": dt, "query": query, "results": results, "cache_hit": False}


def run_stat_analysis(
    city_id: int,
    dt: str,
    method: str,
    rationale: str,
    decision_use: str,
) -> dict[str, Any]:
    """Gated statistical analysis tool.

    Requires non-empty rationale and decision_use before executing any computation.
    Gated by RCA_STAT_TOOLS_ENABLED (default true).
    """
    from rca.config import get_stat_tools_enabled

    if not get_stat_tools_enabled():
        return {"error": "Statistical tools are disabled (RCA_STAT_TOOLS_ENABLED=false)."}
    if not rationale.strip():
        return {"error": "rationale must be non-empty. Explain why this analysis is needed."}
    if not decision_use.strip():
        return {"error": "decision_use must be non-empty. Explain what decision this analysis supports."}

    if method == "robust_baseline_check":
        result = compare_same_weekday_baseline(city_id, dt)
        return {"method": method, "rationale": rationale, "decision_use": decision_use, **result}

    if method == "driver_shift_scan":
        result = detect_intraday_shift(city_id, dt)
        return {"method": method, "rationale": rationale, "decision_use": decision_use, **result}

    if method == "simple_expected_sales_sanity_check":
        signal = get_signal_evidence(city_id, dt)
        current = signal.get("current_sales")
        expected = signal.get("expected_sales")
        deviation_pct = signal.get("deviation_pct")
        check = "pass" if deviation_pct is not None and abs(float(deviation_pct)) >= 10.0 else "warn_borderline"
        return {
            "method": method,
            "rationale": rationale,
            "decision_use": decision_use,
            "city_id": city_id,
            "dt": dt,
            "current_sales": current,
            "expected_sales": expected,
            "deviation_pct": deviation_pct,
            "sanity_check": check,
            "interpretation": (
                "Signal deviation exceeds 10% threshold — move is material."
                if check == "pass"
                else "Deviation is below 10% — move may be borderline or noise."
            ),
        }

    return {"error": f"Unknown method '{method}'. Valid: robust_baseline_check, driver_shift_scan, simple_expected_sales_sanity_check."}


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_signal_evidence": {
        "description": "Get the city/date signal row and expected-sales comparison.",
        "parameters": {
            "type": "object",
            "properties": {"city_id": {"type": "integer"}, "dt": {"type": "string"}},
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_signal_evidence,
    },
    "get_sales_context": {
        "description": "Get recent sales history and city/date sales facts.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "history_days": {"type": "integer", "minimum": 3, "maximum": 30, "default": 14},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_sales_context,
    },
    "get_inventory_context": {
        "description": "Get stockout and availability facts for one city/date.",
        "parameters": {
            "type": "object",
            "properties": {"city_id": {"type": "integer"}, "dt": {"type": "string"}},
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_inventory_context,
    },
    "get_pricing_context": {
        "description": "Get discount facts for one city/date.",
        "parameters": {
            "type": "object",
            "properties": {"city_id": {"type": "integer"}, "dt": {"type": "string"}},
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_pricing_context,
    },
    "get_promotions_context": {
        "description": "Get unlabeled activity flag facts for one city/date.",
        "parameters": {
            "type": "object",
            "properties": {"city_id": {"type": "integer"}, "dt": {"type": "string"}},
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_promotions_context,
    },
    "get_calendar_weather_context": {
        "description": "Get holiday, weekday, weekend, and weather context for one city/date.",
        "parameters": {
            "type": "object",
            "properties": {"city_id": {"type": "integer"}, "dt": {"type": "string"}},
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_calendar_weather_context,
    },
    "get_intraday_profile": {
        "description": "Get hourly sales share and hourly stockout rates for one city/date.",
        "parameters": {
            "type": "object",
            "properties": {"city_id": {"type": "integer"}, "dt": {"type": "string"}},
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": get_intraday_profile,
    },
    "compare_recent_baseline": {
        "description": "Compare current sales to a recent rolling baseline.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "window": {"type": "integer", "minimum": 3, "maximum": 28, "default": 7},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": compare_recent_baseline,
    },
    "compare_same_weekday_baseline": {
        "description": "Compare current sales to prior same-weekday history.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "weeks": {"type": "integer", "minimum": 2, "maximum": 8, "default": 4},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": compare_same_weekday_baseline,
    },
    "detect_intraday_shift": {
        "description": "Compare the current intraday sales shape to recent history.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "lookback_days": {"type": "integer", "minimum": 3, "maximum": 21, "default": 7},
            },
            "required": ["city_id", "dt"],
            "additionalProperties": False,
        },
        "function": detect_intraday_shift,
    },
    "get_memory_context": {
        "description": "Retrieve recent lessons and outcome summaries for the city.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["city_id"],
            "additionalProperties": False,
        },
        "function": get_memory_context,
    },
    "search_external_events": {
        "description": "Search the web for external events or news that may explain the city/date move.",
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "query": {"type": "string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": DEFAULT_NEWS_RESULTS},
            },
            "required": ["city_id", "dt", "query"],
            "additionalProperties": False,
        },
        "function": search_external_events,
    },
    "run_stat_analysis": {
        "description": (
            "Gated statistical analysis tool. Requires a non-empty rationale (why this analysis is needed) "
            "and decision_use (what decision this supports) before running. "
            "Methods: robust_baseline_check (same-weekday baseline), "
            "driver_shift_scan (intraday shape comparison), "
            "simple_expected_sales_sanity_check (signal deviation check)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city_id": {"type": "integer"},
                "dt": {"type": "string"},
                "method": {
                    "type": "string",
                    "enum": ["robust_baseline_check", "driver_shift_scan", "simple_expected_sales_sanity_check"],
                },
                "rationale": {"type": "string", "description": "Why this analysis is needed for this investigation."},
                "decision_use": {"type": "string", "description": "What decision or hypothesis this analysis will support."},
            },
            "required": ["city_id", "dt", "method", "rationale", "decision_use"],
            "additionalProperties": False,
        },
        "function": run_stat_analysis,
    },
}


def get_tool_schemas(tool_names: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    names = list(tool_names) if tool_names is not None else list(TOOL_REGISTRY.keys())
    schemas = []
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
        if "history_days" in coerced:
            coerced["history_days"] = int(coerced["history_days"])
        if "window" in coerced:
            coerced["window"] = int(coerced["window"])
        if "weeks" in coerced:
            coerced["weeks"] = int(coerced["weeks"])
        if "lookback_days" in coerced:
            coerced["lookback_days"] = int(coerced["lookback_days"])
        return function(**coerced)
    except Exception as exc:
        return {"error": str(exc)}
