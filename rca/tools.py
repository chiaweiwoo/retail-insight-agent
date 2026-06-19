from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

import pandas as pd
from duckduckgo_search import DDGS

from rca.config import (
    DEFAULT_DROP_THRESHOLD_PCT,
    DEFAULT_LIFT_THRESHOLD_PCT,
    DEFAULT_SIGNAL_METRIC,
)
from rca.evidence import get_store_day_evidence
from rca.outcomes import get_prior_rca as load_prior_rca
from rca.signals import build_sales_signal_frame, load_sales_history


ToolFunction = Callable[..., dict[str, Any]]


def _round_float(value: float | None, digits: int = 4) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


@lru_cache(maxsize=1)
def _signal_frame() -> pd.DataFrame:
    frame = load_sales_history()
    signals = build_sales_signal_frame(frame)
    signals["dt_label"] = signals["dt"].dt.strftime("%Y-%m-%d")
    return signals


def _get_signal_row(store_alias: str, dt: str) -> pd.Series:
    frame = _signal_frame()
    matched = frame[
        (frame["store_alias"] == store_alias)
        & (frame["dt_label"] == dt)
    ]
    if matched.empty:
        raise ValueError(f"No signal row found for store_alias={store_alias} dt={dt}")
    return matched.iloc[0]


def _get_history_slice(store_alias: str, dt: str, days: int = 7) -> pd.DataFrame:
    frame = _signal_frame()
    store_frame = frame[frame["store_alias"] == store_alias].sort_values("dt")
    matched = store_frame.index[store_frame["dt_label"] == dt]
    if len(matched) != 1:
        raise ValueError(f"No history row found for store_alias={store_alias} dt={dt}")
    store_frame = store_frame.reset_index(drop=True)
    pos = int(store_frame.index[store_frame["dt_label"] == dt][0])
    start = max(0, pos - days)
    return store_frame.iloc[start : pos + 1].copy()


def _signal_label(
    signal_value: float | None,
    drop_threshold_pct: float,
    lift_threshold_pct: float,
) -> str:
    if signal_value is None or pd.isna(signal_value):
        return "insufficient_history"
    if float(signal_value) <= drop_threshold_pct:
        return "drop"
    if float(signal_value) >= lift_threshold_pct:
        return "lift"
    return "neutral"


def get_signal_evidence(
    store_alias: str,
    dt: str,
    metric: str = DEFAULT_SIGNAL_METRIC,
    drop_threshold_pct: float = DEFAULT_DROP_THRESHOLD_PCT,
    lift_threshold_pct: float = DEFAULT_LIFT_THRESHOLD_PCT,
) -> dict[str, Any]:
    row = _get_signal_row(store_alias, dt)
    signal_value = row.get(metric)
    return {
        "store_alias": store_alias,
        "dt": dt,
        "metric": metric,
        "signal_label": _signal_label(signal_value, drop_threshold_pct, lift_threshold_pct),
        "thresholds": {
            "drop_lte_pct": drop_threshold_pct,
            "lift_gte_pct": lift_threshold_pct,
        },
        "current_sales": _round_float(row["total_sales"]),
        "previous_day_sales": _round_float(row["previous_day_sales"]),
        "trailing_7d_avg_sales": _round_float(row["trailing_7d_avg_sales"]),
        "same_weekday_4w_avg_sales": _round_float(row["same_weekday_4w_avg_sales"]),
        "day_over_day_pct_change": _round_float(row["day_over_day_pct_change"]),
        "trailing_7d_pct_change": _round_float(row["trailing_7d_pct_change"]),
        "same_weekday_4w_pct_change": _round_float(row["same_weekday_4w_pct_change"]),
        "weekday": str(row["weekday"]),
        "holiday_name_inferred": str(row["holiday_name_inferred"]),
    }


def get_sales_context(store_alias: str, dt: str, history_days: int = 7) -> dict[str, Any]:
    signal_row = _get_signal_row(store_alias, dt)
    history = _get_history_slice(store_alias, dt, days=history_days)
    rows = [
        {
            "dt": str(row.dt.strftime("%Y-%m-%d")),
            "total_sales": _round_float(row.total_sales),
            "weekday": str(row.weekday),
            "holiday_name_inferred": str(row.holiday_name_inferred),
        }
        for row in history.itertuples(index=False)
    ]
    return {
        "store_alias": store_alias,
        "dt": dt,
        "history_window_days": history_days,
        "current_total_sales": _round_float(signal_row["total_sales"]),
        "history": rows,
        "sales_baselines": {
            "previous_day_sales": _round_float(signal_row["previous_day_sales"]),
            "trailing_7d_avg_sales": _round_float(signal_row["trailing_7d_avg_sales"]),
            "same_weekday_4w_avg_sales": _round_float(signal_row["same_weekday_4w_avg_sales"]),
        },
    }


def get_stockout_context(store_alias: str, dt: str) -> dict[str, Any]:
    record = get_store_day_evidence(store_alias, dt)
    history = _get_history_slice(store_alias, dt, days=7)
    matched = history[history["dt_label"] == dt].iloc[0]
    trailing_avg = _round_float(history["total_sales"].iloc[:-1].mean()) if len(history) > 1 else None
    return {
        "store_alias": store_alias,
        "dt": dt,
        "avg_stockout_hours": _round_float(record["stockout"]["avg_stockout_hours"]),
        "stockout_product_rate": _round_float(record["stockout"]["stockout_product_rate"]),
        "severe_stockout_product_rate": _round_float(
            record["stockout"]["severe_stockout_product_rate"]
        ),
        "full_stockout_product_rate": _round_float(record["stockout"]["full_stockout_product_rate"]),
        "hourly_stockout_rate_peak": _round_float(max(record["stockout"]["hourly_stockout_rate"])),
        "current_total_sales": _round_float(matched["total_sales"]),
        "recent_avg_sales": trailing_avg,
    }


def get_discount_context(store_alias: str, dt: str) -> dict[str, Any]:
    record = get_store_day_evidence(store_alias, dt)
    return {
        "store_alias": store_alias,
        "dt": dt,
        "avg_discount": _round_float(record["discount"]["avg_discount"]),
        "discounted_product_rate": _round_float(record["discount"]["discounted_product_rate"]),
        "deep_discount_product_rate": _round_float(
            record["discount"]["deep_discount_product_rate"]
        ),
    }


def get_activity_context(store_alias: str, dt: str) -> dict[str, Any]:
    record = get_store_day_evidence(store_alias, dt)
    return {
        "store_alias": store_alias,
        "dt": dt,
        "activity_product_rate": _round_float(record["activity"]["activity_product_rate"]),
        "activity_sales_share": _round_float(record["activity"]["activity_sales_share"]),
    }


def get_calendar_weather_context(store_alias: str, dt: str) -> dict[str, Any]:
    record = get_store_day_evidence(store_alias, dt)
    return {
        "store_alias": store_alias,
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


def get_peer_store_context(store_alias: str, dt: str) -> dict[str, Any]:
    row = _get_signal_row(store_alias, dt)
    frame = _signal_frame()
    prefix_group = store_alias[0]
    daily = frame[frame["dt_label"] == dt].copy()
    prefix_daily = daily[daily["store_alias"].str.startswith(prefix_group)]
    overall_avg = _round_float(daily["total_sales"].mean())
    prefix_avg = _round_float(prefix_daily["total_sales"].mean())
    rank = int(
        daily["total_sales"].rank(method="min", ascending=False)[daily["store_alias"] == store_alias].iloc[0]
    )
    prefix_rank = int(
        prefix_daily["total_sales"]
        .rank(method="min", ascending=False)[prefix_daily["store_alias"] == store_alias]
        .iloc[0]
    )
    return {
        "store_alias": store_alias,
        "dt": dt,
        "store_prefix_group": prefix_group,
        "store_total_sales": _round_float(row["total_sales"]),
        "prefix_group_avg_sales_same_day": prefix_avg,
        "overall_avg_sales_same_day": overall_avg,
        "overall_rank_same_day": rank,
        "overall_store_count": int(daily.shape[0]),
        "prefix_group_rank_same_day": prefix_rank,
        "prefix_group_store_count": int(prefix_daily.shape[0]),
        # Backward-compatible aliases for older prompts/tests/artifacts.
        "store_tier": prefix_group,
        "tier_avg_sales_same_day": prefix_avg,
        "tier_rank_same_day": prefix_rank,
        "tier_store_count": int(prefix_daily.shape[0]),
    }


def search_news(query: str, max_results: int = 5) -> dict[str, Any]:
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


def get_prior_rca(store_alias: str) -> dict[str, Any]:
    return load_prior_rca(store_alias)


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "get_signal_evidence": {
        "description": "Get the precomputed store-day sales trigger signal and baseline comparisons.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
                "dt": {"type": "string"},
            },
            "required": ["store_alias", "dt"],
            "additionalProperties": False,
        },
        "function": get_signal_evidence,
    },
    "get_sales_context": {
        "description": "Get current sales plus recent store sales history and baseline windows.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
                "dt": {"type": "string"},
                "history_days": {"type": "integer", "minimum": 3, "maximum": 14},
            },
            "required": ["store_alias", "dt"],
            "additionalProperties": False,
        },
        "function": get_sales_context,
    },
    "get_stockout_context": {
        "description": "Get stockout evidence for one store-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
                "dt": {"type": "string"},
            },
            "required": ["store_alias", "dt"],
            "additionalProperties": False,
        },
        "function": get_stockout_context,
    },
    "get_discount_context": {
        "description": "Get discount evidence for one store-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
                "dt": {"type": "string"},
            },
            "required": ["store_alias", "dt"],
            "additionalProperties": False,
        },
        "function": get_discount_context,
    },
    "get_activity_context": {
        "description": "Get promotional activity evidence for one store-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
                "dt": {"type": "string"},
            },
            "required": ["store_alias", "dt"],
            "additionalProperties": False,
        },
        "function": get_activity_context,
    },
    "get_calendar_weather_context": {
        "description": "Get holiday, weekday, weekend, and weather context for one store-day.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
                "dt": {"type": "string"},
            },
            "required": ["store_alias", "dt"],
            "additionalProperties": False,
        },
        "function": get_calendar_weather_context,
    },
    "get_peer_store_context": {
        "description": "Compare the store against same-day peers and its same-prefix peer group.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
                "dt": {"type": "string"},
            },
            "required": ["store_alias", "dt"],
            "additionalProperties": False,
        },
        "function": get_peer_store_context,
    },
    "search_news": {
        "description": "Search the web for news or events relevant to a retail sales move. Pass a focused query such as 'retail sales China May 2024' or 'holiday shopping event May 16 2024'.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query string"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "function": search_news,
    },
    "get_prior_rca": {
        "description": "Get prior RCA outcomes for this store from the local run history.",
        "parameters": {
            "type": "object",
            "properties": {
                "store_alias": {"type": "string"},
            },
            "required": ["store_alias"],
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
        return function(**arguments)
    except Exception as e:
        return {"error": str(e)}
