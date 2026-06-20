from __future__ import annotations

from fastmcp import FastMCP

from rca.tools import (
    compare_recent_baseline,
    compare_same_weekday_baseline,
    detect_intraday_shift,
    get_calendar_weather_context,
    get_intraday_profile,
    get_inventory_context,
    get_memory_context,
    get_pricing_context,
    get_promotions_context,
    get_sales_context,
    get_signal_evidence,
    search_external_events,
)

mcp = FastMCP("retail-rca")


@mcp.tool()
def signal_evidence(city_id: int, dt: str) -> dict:
    return get_signal_evidence(city_id, dt)


@mcp.tool()
def sales_context(city_id: int, dt: str, history_days: int = 14) -> dict:
    return get_sales_context(city_id, dt, history_days)


@mcp.tool()
def inventory_context(city_id: int, dt: str) -> dict:
    return get_inventory_context(city_id, dt)


@mcp.tool()
def pricing_context(city_id: int, dt: str) -> dict:
    return get_pricing_context(city_id, dt)


@mcp.tool()
def promotions_context(city_id: int, dt: str) -> dict:
    return get_promotions_context(city_id, dt)


@mcp.tool()
def calendar_weather_context(city_id: int, dt: str) -> dict:
    return get_calendar_weather_context(city_id, dt)


@mcp.tool()
def intraday_profile(city_id: int, dt: str) -> dict:
    return get_intraday_profile(city_id, dt)


@mcp.tool()
def recent_baseline(city_id: int, dt: str, window: int = 7) -> dict:
    return compare_recent_baseline(city_id, dt, window)


@mcp.tool()
def same_weekday_baseline(city_id: int, dt: str, weeks: int = 4) -> dict:
    return compare_same_weekday_baseline(city_id, dt, weeks)


@mcp.tool()
def intraday_shift(city_id: int, dt: str, lookback_days: int = 7) -> dict:
    return detect_intraday_shift(city_id, dt, lookback_days)


@mcp.tool()
def memory_context(city_id: int, limit: int = 5) -> dict:
    return get_memory_context(city_id, limit)


@mcp.tool()
def external_events(city_id: int, dt: str, query: str, max_results: int = 5) -> dict:
    return search_external_events(city_id, dt, query, max_results)
