from __future__ import annotations

from rca.tools import (
    execute_tool,
    get_activity_context,
    get_calendar_weather_context,
    get_discount_context,
    get_prior_rca,
    get_peer_store_context,
    get_sales_context,
    get_signal_evidence,
    get_stockout_context,
    get_tool_schemas,
)


def test_signal_tool_returns_drop_label_for_benchmark_case() -> None:
    result = get_signal_evidence("h555", "2024-05-16")
    assert result["signal_label"] == "drop"
    assert result["trailing_7d_pct_change"] is not None
    assert result["trailing_7d_pct_change"] <= -20.0


def test_sales_tool_returns_history_window() -> None:
    result = get_sales_context("m041", "2024-05-12", history_days=5)
    assert result["store_alias"] == "m041"
    assert result["dt"] == "2024-05-12"
    assert len(result["history"]) == 6
    assert result["history"][-1]["dt"] == "2024-05-12"


def test_domain_tools_return_expected_keys() -> None:
    stockout = get_stockout_context("h263", "2024-06-24")
    discount = get_discount_context("h263", "2024-06-24")
    activity = get_activity_context("h263", "2024-06-24")
    calendar_weather = get_calendar_weather_context("h263", "2024-06-24")
    peer = get_peer_store_context("h263", "2024-06-24")

    assert "stockout_product_rate" in stockout
    assert "avg_discount" in discount
    assert "activity_sales_share" in activity
    assert calendar_weather["holiday_name_inferred"] == "normal_weekday"
    assert peer["store_prefix_group"] == "h"
    assert peer["prefix_group_avg_sales_same_day"] is not None


def test_tool_registry_and_execute_tool_work() -> None:
    schemas = get_tool_schemas()
    names = {tool["function"]["name"] for tool in schemas}
    assert "get_signal_evidence" in names
    assert "get_prior_rca" in names
    result = execute_tool("get_discount_context", {"store_alias": "h263", "dt": "2024-06-24"})
    assert result["store_alias"] == "h263"


def test_get_prior_rca_returns_empty_summary_when_no_history() -> None:
    result = get_prior_rca("h263")
    assert result["store_alias"] == "h263"
    assert "previous_trigger_count" in result
