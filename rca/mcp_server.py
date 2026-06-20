from fastmcp import FastMCP
from rca.tools import (
    get_signal_evidence, get_sales_context, get_stockout_context,
    get_stockout_baseline, get_discount_context, get_activity_context,
    get_calendar_weather_context, get_peer_store_context, get_prior_rca,
)

mcp = FastMCP("retail-rca")

@mcp.tool()
def signal_evidence(city_id: int, dt: str) -> dict:
    """Get signal evidence for a store on a given date.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_signal_evidence(city_id, dt)

@mcp.tool()
def sales_context(city_id: int, dt: str, history_days: int = 7) -> dict:
    """Get current sales plus recent store sales history and baseline windows.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_sales_context(city_id, dt, history_days)

@mcp.tool()
def stockout_context(city_id: int, dt: str) -> dict:
    """Get stockout evidence for one store-day.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_stockout_context(city_id, dt)

@mcp.tool()
def stockout_baseline(city_id: int, dt: str, window: int = 30) -> dict:
    """Get this store's rolling stockout baseline for the N days before the trigger date.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_stockout_baseline(city_id, dt, window)

@mcp.tool()
def discount_context(city_id: int, dt: str) -> dict:
    """Get discount evidence for one store-day.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_discount_context(city_id, dt)

@mcp.tool()
def activity_context(city_id: int, dt: str) -> dict:
    """Get promotional activity evidence for one store-day.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_activity_context(city_id, dt)

@mcp.tool()
def calendar_weather_context(city_id: int, dt: str) -> dict:
    """Get holiday, weekday, weekend, and weather context for one store-day.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_calendar_weather_context(city_id, dt)

@mcp.tool()
def peer_store_context(city_id: int, dt: str) -> dict:
    """Compare the store against same-day peers and its same-prefix peer group.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_peer_store_context(city_id, dt)

@mcp.tool()
def prior_rca(city_id: int) -> dict:
    """Get prior RCA outcomes for this store from the local run history.
    Caveats: sales figures are normalized coefficients (not currency).
    Peer comparisons come from a 15-store local sandbox — treat as weak priors.
    """
    return get_prior_rca(city_id)
