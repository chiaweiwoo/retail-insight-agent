"""Signal computation: actuals vs business target → drop/lift/neutral labels.

Called by `rca analyze`. Populates rca_city_signal in Supabase.
"""
from __future__ import annotations

import pandas as pd

from rca.config import (
    BUSINESS_TARGET_GROWTH_FACTOR,
    DEFAULT_DROP_THRESHOLD_PCT,
    DEFAULT_LIFT_THRESHOLD_PCT,
    make_supabase_client,
)

_MIN_BASELINE_OBS = 3


def build_signal_series(actuals_df: pd.DataFrame, forecast_df: pd.DataFrame) -> pd.DataFrame:
    """Merge actuals with finance forecast, apply business target, label each city-day.

    actuals_df columns required: city_id, dt, total_sales, weekday, density_tier,
                                  holiday_name_inferred
    forecast_df columns required: city_id, dt, forecast_sales

    Returns a DataFrame ready for push_city_signal(), with signal_label set and
    rolling-baseline context columns included for agent tools.
    """
    df = actuals_df[
        ["city_id", "dt", "total_sales", "weekday", "density_tier", "holiday_name_inferred"]
    ].copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["city_id", "dt"]).reset_index(drop=True)

    forecast = forecast_df[["city_id", "dt"]].copy()
    forecast["dt"] = pd.to_datetime(forecast["dt"])
    forecast["forecast_sales"] = forecast_df["forecast_sales"].values
    df = df.merge(forecast, on=["city_id", "dt"], how="left")

    # Business target = statistical forecast × growth factor
    df["business_target"] = df["forecast_sales"] * BUSINESS_TARGET_GROWTH_FACTOR

    # Rolling baselines
    by_city = df.groupby("city_id", group_keys=False)
    df["previous_day_sales"] = by_city["total_sales"].shift(1)
    df["trailing_7d_avg_sales"] = by_city["total_sales"].transform(
        lambda s: s.shift(1).rolling(window=7, min_periods=_MIN_BASELINE_OBS).mean()
    )
    by_city_dow = df.groupby(["city_id", df["dt"].dt.dayofweek], group_keys=False)
    df["same_weekday_4w_avg_sales"] = by_city_dow["total_sales"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=_MIN_BASELINE_OBS).mean()
    )

    # Pct-change context
    def _pct(current: pd.Series, base: pd.Series) -> pd.Series:
        return ((current - base) / base * 100.0).where(base > 0)

    df["day_over_day_pct_change"] = _pct(df["total_sales"], df["previous_day_sales"])
    df["trailing_7d_pct_change"] = _pct(df["total_sales"], df["trailing_7d_avg_sales"])
    df["same_weekday_4w_pct_change"] = _pct(df["total_sales"], df["same_weekday_4w_avg_sales"])
    df["target_deviation_pct"] = _pct(df["total_sales"], df["business_target"])

    # Signal label
    def _label(row: pd.Series) -> str:
        if pd.isna(row["business_target"]):
            return "insufficient_history"
        if row["target_deviation_pct"] <= DEFAULT_DROP_THRESHOLD_PCT:
            return "drop"
        if row["target_deviation_pct"] >= DEFAULT_LIFT_THRESHOLD_PCT:
            return "lift"
        return "neutral"

    df["signal_label"] = df.apply(_label, axis=1)
    df["dt"] = df["dt"].dt.strftime("%Y-%m-%d")

    return df[[
        "city_id", "dt", "total_sales", "business_target", "target_deviation_pct",
        "signal_label", "previous_day_sales", "trailing_7d_avg_sales",
        "same_weekday_4w_avg_sales", "day_over_day_pct_change", "trailing_7d_pct_change",
        "same_weekday_4w_pct_change", "weekday", "density_tier", "holiday_name_inferred",
    ]]


def get_trigger_dates_for_city(city_id: int) -> list[str]:
    """Return sorted list of triggered (drop/lift) dates for a city from rca_city_signal."""
    client = make_supabase_client()
    resp = (
        client.table("rca_city_signal")
        .select("dt,signal_label")
        .eq("city_id", city_id)
        .in_("signal_label", ["drop", "lift"])
        .order("dt")
        .execute()
    )
    return [row["dt"] for row in (resp.data or [])]
