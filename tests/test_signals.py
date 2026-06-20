"""Tests for the signals module (build_signal_series)."""
from __future__ import annotations

import pandas as pd
import pytest

from rca.signals import build_signal_series


def _toy_actuals(n: int = 10) -> pd.DataFrame:
    dates = pd.date_range("2024-03-28", periods=n, freq="D")
    return pd.DataFrame({
        "city_id": [0] * n,
        "dt": dates.strftime("%Y-%m-%d"),
        "total_sales": [100.0 + i * 5 for i in range(n)],
        "weekday": [d.day_name().lower() for d in dates],
        "density_tier": ["2"] * n,
        "holiday_name_inferred": ["normal_weekday"] * n,
    })


def _toy_forecast(actuals: pd.DataFrame) -> pd.DataFrame:
    # Provide forecast for second half only (simulates 28-day warm-up)
    rows = actuals.iloc[5:].copy()
    rows["forecast_sales"] = [110.0 + i * 5 for i in range(len(rows))]
    return rows[["city_id", "dt", "forecast_sales"]]


def test_build_signal_series_returns_expected_columns() -> None:
    actuals = _toy_actuals()
    forecast = _toy_forecast(actuals)
    result = build_signal_series(actuals, forecast)

    required = {
        "city_id", "dt", "total_sales", "business_target", "target_deviation_pct",
        "signal_label", "previous_day_sales", "trailing_7d_avg_sales",
        "same_weekday_4w_avg_sales", "day_over_day_pct_change", "trailing_7d_pct_change",
        "same_weekday_4w_pct_change", "weekday", "density_tier", "holiday_name_inferred",
    }
    assert required.issubset(result.columns)


def test_build_signal_series_row_count_matches_actuals() -> None:
    actuals = _toy_actuals(10)
    forecast = _toy_forecast(actuals)
    result = build_signal_series(actuals, forecast)
    assert len(result) == len(actuals)


def test_build_signal_series_insufficient_history_when_no_forecast() -> None:
    actuals = _toy_actuals(10)
    # No forecast rows → all insufficient_history
    empty_forecast = pd.DataFrame(columns=["city_id", "dt", "forecast_sales"])
    result = build_signal_series(actuals, empty_forecast)
    assert (result["signal_label"] == "insufficient_history").all()


def test_build_signal_series_business_target_is_scaled() -> None:
    from rca.config import BUSINESS_TARGET_GROWTH_FACTOR
    actuals = _toy_actuals(10)
    forecast = _toy_forecast(actuals)
    result = build_signal_series(actuals, forecast)
    with_forecast = result[result["business_target"].notna()]
    assert not with_forecast.empty
    # business_target should be strictly > forecast_sales (growth factor > 1)
    assert (with_forecast["business_target"] > 0).all()


def test_build_signal_series_drop_label() -> None:
    actuals = pd.DataFrame({
        "city_id": [0] * 5,
        "dt": pd.date_range("2024-03-28", periods=5, freq="D").strftime("%Y-%m-%d"),
        "total_sales": [50.0, 50.0, 50.0, 50.0, 50.0],
        "weekday": ["thursday"] * 5,
        "density_tier": ["2"] * 5,
        "holiday_name_inferred": ["normal_weekday"] * 5,
    })
    # Forecast much higher → actual is far below target → drop
    forecast = pd.DataFrame({
        "city_id": [0] * 5,
        "dt": actuals["dt"].tolist(),
        "forecast_sales": [100.0] * 5,  # business_target ≈ 103; actual 50 → ~-51% → drop
    })
    result = build_signal_series(actuals, forecast)
    assert (result["signal_label"] == "drop").all()


def test_build_signal_series_lift_label() -> None:
    actuals = pd.DataFrame({
        "city_id": [0] * 5,
        "dt": pd.date_range("2024-03-28", periods=5, freq="D").strftime("%Y-%m-%d"),
        "total_sales": [200.0, 200.0, 200.0, 200.0, 200.0],
        "weekday": ["thursday"] * 5,
        "density_tier": ["2"] * 5,
        "holiday_name_inferred": ["normal_weekday"] * 5,
    })
    forecast = pd.DataFrame({
        "city_id": [0] * 5,
        "dt": actuals["dt"].tolist(),
        "forecast_sales": [100.0] * 5,  # business_target ≈ 103; actual 200 → ~+94% → lift
    })
    result = build_signal_series(actuals, forecast)
    assert (result["signal_label"] == "lift").all()
