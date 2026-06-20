"""ETL pipeline: parquet → pandas aggregation → Supabase.

No local database. DuckDB is gone. The pipeline:
  1. load_scoped_raw_data()   — read parquet, scope to CITY_IDS
  2. build_all_tables()       — produce dimension + fact DataFrames
  3. ingest_to_supabase()     — merge and push all tables to Supabase

All runtime reads (rca run) go directly to Supabase.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rca.config import (
    CITY_IDS,
    DATE_END,
    DATE_START,
    EXPECTED_DAY_COUNT,
    HOURLY_LENGTH,
    RAW_DATA_PATH,
    REQUIRED_RAW_COLUMNS,
    make_supabase_client,
)


# ---------------------------------------------------------------------------
# Raw data loading
# ---------------------------------------------------------------------------


def _hour_columns(prefix: str) -> list[str]:
    return [f"hour_{hour:02d}_{prefix}" for hour in range(HOURLY_LENGTH)]


def _validate_required_columns(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_RAW_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Raw parquet is missing required columns: {missing}")


def _validate_scope_counts(scoped: pd.DataFrame) -> None:
    day_count = int(scoped["dt"].nunique())
    if day_count != EXPECTED_DAY_COUNT:
        raise ValueError(f"Expected {EXPECTED_DAY_COUNT} dates, found {day_count}.")
    min_date = scoped["dt"].min().strftime("%Y-%m-%d")
    max_date = scoped["dt"].max().strftime("%Y-%m-%d")
    if min_date != DATE_START or max_date != DATE_END:
        raise ValueError(
            f"Expected date range {DATE_START} to {DATE_END}, found {min_date} to {max_date}."
        )
    city_count = int(scoped["city_id"].nunique())
    print(f"  Scope: {city_count} cities, {day_count} days.")


def _validate_hourly_lists(series: pd.Series, column_name: str) -> None:
    null_count = int(series.isna().sum())
    if null_count:
        raise ValueError(f"Column {column_name} contains {null_count} null hourly arrays.")
    bad_lengths = series.map(len).ne(HOURLY_LENGTH)
    if bool(bad_lengths.any()):
        raise ValueError(
            f"Column {column_name} contains {int(bad_lengths.sum())} malformed hourly arrays. "
            f"Expected length {HOURLY_LENGTH}."
        )


def _infer_holiday_name(dt: pd.Timestamp) -> str:
    s = dt.strftime("%Y-%m-%d")
    if "2024-04-04" <= s <= "2024-04-06":
        return "qingming_period"
    if "2024-05-01" <= s <= "2024-05-05":
        return "labor_day_period"
    if "2024-06-08" <= s <= "2024-06-10":
        return "dragon_boat_period"
    if dt.weekday() >= 5:
        return "weekend"
    return "normal_weekday"


def load_scoped_raw_data(raw_data_path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    if not raw_data_path.exists():
        raise FileNotFoundError(f"Raw parquet is missing: {raw_data_path}")
    frame = pd.read_parquet(raw_data_path)
    _validate_required_columns(frame)
    scoped = frame.loc[frame["city_id"].isin(CITY_IDS)].copy()
    if scoped.empty:
        raise ValueError("Scoped raw data is empty.")
    scoped["dt"] = pd.to_datetime(scoped["dt"], format="%Y-%m-%d", errors="raise")
    _validate_hourly_lists(scoped["hours_sale"], "hours_sale")
    _validate_hourly_lists(scoped["hours_stock_status"], "hours_stock_status")
    _validate_scope_counts(scoped)
    return scoped


# ---------------------------------------------------------------------------
# Dimension and fact builders (pure pandas, no DB)
# ---------------------------------------------------------------------------


def build_dim_city(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped.groupby("city_id", as_index=False)
        .agg(store_count=("store_id", "nunique"))
        .sort_values("city_id")
        .reset_index(drop=True)
    )


def build_dim_holiday_day(scoped: pd.DataFrame) -> pd.DataFrame:
    holiday = (
        scoped.groupby("dt", as_index=False)
        .agg(holiday_flag=("holiday_flag", "max"))
        .sort_values("dt")
        .reset_index(drop=True)
    )
    holiday["weekday"] = holiday["dt"].dt.day_name().str.lower()
    holiday["is_weekend"] = holiday["dt"].dt.weekday >= 5
    holiday["holiday_flag"] = holiday["holiday_flag"].astype(bool)
    holiday["holiday_name_inferred"] = holiday["dt"].map(_infer_holiday_name)
    holiday["holiday_note"] = (
        "Inferred from project date rules; source dataset only provides holiday_flag."
    )
    return holiday[
        ["dt", "weekday", "is_weekend", "holiday_flag", "holiday_name_inferred", "holiday_note"]
    ]


def build_dim_weather_day(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped.groupby("dt", as_index=False)
        .agg(
            precpt=("precpt", "mean"),
            avg_temperature=("avg_temperature", "mean"),
            avg_humidity=("avg_humidity", "mean"),
            avg_wind_level=("avg_wind_level", "mean"),
        )
        .sort_values("dt")
        .reset_index(drop=True)
    )


def _expand_hourly_column(
    scoped: pd.DataFrame,
    source_column: str,
    output_suffix: str,
) -> pd.DataFrame:
    return pd.DataFrame(
        scoped[source_column].tolist(),
        columns=_hour_columns(output_suffix),
        index=scoped.index,
    ).astype(float)


def build_fact_sales_city_day(scoped: pd.DataFrame) -> pd.DataFrame:
    sales = pd.concat(
        [
            scoped[["city_id", "dt", "product_id", "sale_amount"]],
            _expand_hourly_column(scoped, "hours_sale", "sales"),
        ],
        axis=1,
    )
    return (
        sales.groupby(["city_id", "dt"], as_index=False)
        .agg(
            product_count=("product_id", "count"),
            active_product_count=("sale_amount", lambda s: int((s > 0).sum())),
            total_sales=("sale_amount", "sum"),
            avg_sales_per_product=("sale_amount", "mean"),
            **{col: (col, "sum") for col in _hour_columns("sales")},
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
    )


def build_fact_stockout_city_day(scoped: pd.DataFrame) -> pd.DataFrame:
    stockout = pd.concat(
        [
            scoped[["city_id", "dt", "stock_hour6_22_cnt"]],
            _expand_hourly_column(scoped, "hours_stock_status", "stockout_rate"),
        ],
        axis=1,
    )
    return (
        stockout.groupby(["city_id", "dt"], as_index=False)
        .agg(
            avg_stockout_hours=("stock_hour6_22_cnt", "mean"),
            stockout_product_rate=("stock_hour6_22_cnt", lambda s: float((s > 0).mean())),
            severe_stockout_product_rate=("stock_hour6_22_cnt", lambda s: float((s >= 8).mean())),
            full_stockout_product_rate=("stock_hour6_22_cnt", lambda s: float((s == 16).mean())),
            **{col: (col, "mean") for col in _hour_columns("stockout_rate")},
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
    )


def build_fact_discount_city_day(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped.groupby(["city_id", "dt"], as_index=False)
        .agg(
            avg_discount=("discount", "mean"),
            discounted_product_rate=("discount", lambda s: float((s < 0.999).mean())),
            deep_discount_product_rate=("discount", lambda s: float((s < 0.5).mean())),
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
    )


def build_fact_activity_city_day(scoped: pd.DataFrame) -> pd.DataFrame:
    grouped = scoped.groupby(["city_id", "dt"], as_index=False)
    activity = grouped.agg(
        activity_product_rate=("activity_flag", "mean"),
        total_sales=("sale_amount", "sum"),
        activity_sales=(
            "sale_amount",
            lambda s: float(s[scoped.loc[s.index, "activity_flag"] == 1].sum()),
        ),
    )
    activity["activity_sales_share"] = activity.apply(
        lambda row: 0.0 if row["total_sales"] == 0
        else float(row["activity_sales"] / row["total_sales"]),
        axis=1,
    )
    return (
        activity[["city_id", "dt", "activity_product_rate", "activity_sales_share"]]
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
    )


def build_all_tables(scoped: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "dim_city": build_dim_city(scoped),
        "dim_holiday_day": build_dim_holiday_day(scoped),
        "dim_weather_day": build_dim_weather_day(scoped),
        "fact_sales_city_day": build_fact_sales_city_day(scoped),
        "fact_stockout_city_day": build_fact_stockout_city_day(scoped),
        "fact_discount_city_day": build_fact_discount_city_day(scoped),
        "fact_activity_city_day": build_fact_activity_city_day(scoped),
    }


# ---------------------------------------------------------------------------
# Supabase-shaped table builders
# ---------------------------------------------------------------------------


def _city_tier(store_count: int) -> str:
    if store_count >= 100:
        return "1"
    if store_count >= 20:
        return "2"
    return "3"


def build_city_series_df(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Merge dimension and fact tables into rca_city_series shape."""
    sales = tables["fact_sales_city_day"]
    stockout = tables["fact_stockout_city_day"]
    discount = tables["fact_discount_city_day"]
    activity = tables["fact_activity_city_day"]
    holiday = tables["dim_holiday_day"]
    weather = tables["dim_weather_day"]
    city = tables["dim_city"]

    df = sales[
        ["city_id", "dt", "total_sales", "product_count", "active_product_count", "avg_sales_per_product"]
    ].merge(city[["city_id", "store_count"]], on="city_id")

    df = df.merge(
        stockout[["city_id", "dt", "avg_stockout_hours", "stockout_product_rate",
                  "severe_stockout_product_rate", "full_stockout_product_rate"]],
        on=["city_id", "dt"],
    )
    df = df.merge(
        discount[["city_id", "dt", "avg_discount", "discounted_product_rate", "deep_discount_product_rate"]],
        on=["city_id", "dt"],
    )
    df = df.merge(
        activity[["city_id", "dt", "activity_product_rate", "activity_sales_share"]],
        on=["city_id", "dt"],
    )
    df = df.merge(
        holiday[["dt", "weekday", "is_weekend", "holiday_flag", "holiday_name_inferred", "holiday_note"]],
        on="dt",
    )
    df = df.merge(
        weather[["dt", "precpt", "avg_temperature", "avg_humidity", "avg_wind_level"]],
        on="dt",
    )

    df["density_tier"] = df["store_count"].map(_city_tier)
    df["dt"] = df["dt"].dt.strftime("%Y-%m-%d")

    return df[[
        "city_id", "density_tier", "dt", "total_sales", "product_count", "active_product_count",
        "avg_sales_per_product",
        "stockout_product_rate", "severe_stockout_product_rate", "avg_stockout_hours",
        "full_stockout_product_rate",
        "avg_discount", "discounted_product_rate", "deep_discount_product_rate",
        "activity_product_rate", "activity_sales_share",
        "holiday_flag", "is_weekend", "weekday", "holiday_name_inferred", "holiday_note",
        "precpt", "avg_temperature", "avg_humidity", "avg_wind_level",
    ]]


def build_city_normals_df(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute per-city percentile/stddev normals and weekday patterns."""
    sales = tables["fact_sales_city_day"]
    city = tables["dim_city"]
    holiday = tables["dim_holiday_day"]

    grouped = sales.groupby("city_id")["total_sales"]
    normals = pd.DataFrame({
        "city_id": grouped.groups.keys(),
        "p25_sale": grouped.quantile(0.25).values,
        "p50_sale": grouped.quantile(0.50).values,
        "p75_sale": grouped.quantile(0.75).values,
        "avg_sale": grouped.mean().values,
        "stddev_sale": grouped.std().values,
    })

    # Weekday DOW average patterns per city
    merged = sales.merge(holiday[["dt", "weekday"]], on="dt")
    dow_avgs = (
        merged.groupby(["city_id", "weekday"])["total_sales"]
        .mean()
        .reset_index()
    )
    dow_map: dict[int, dict[str, float]] = {}
    for _, row in dow_avgs.iterrows():
        dow_map.setdefault(int(row["city_id"]), {})[str(row["weekday"])] = float(row["total_sales"])

    normals["dow_pattern"] = normals["city_id"].map(dow_map)
    normals = normals.merge(city[["city_id", "store_count"]], on="city_id")
    normals["density_tier"] = normals["store_count"].map(_city_tier)

    return normals[["city_id", "density_tier", "p25_sale", "p50_sale", "p75_sale",
                    "avg_sale", "stddev_sale", "dow_pattern"]]


def build_finance_forecast_df(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compute finance S&OP forecast using fleet-share × DOW multiplier model.

    The model needs 28 days of lookback and produces weekly-ahead forecasts.
    First ~28 days have no forecast (returns empty for those dates).
    """
    sales = tables["fact_sales_city_day"]
    holiday = tables["dim_holiday_day"]

    df = sales.merge(holiday[["dt", "weekday"]], on="dt").sort_values("dt")

    # Fleet daily totals
    fleet_daily = (
        df.groupby("dt")["total_sales"].sum().reset_index()
        .rename(columns={"total_sales": "fleet_sales"})
    )
    fleet_daily["dow"] = fleet_daily["dt"].dt.dayofweek

    dates = sorted(df["dt"].unique())
    forecasts: list[dict[str, Any]] = []

    for i in range(28, len(dates), 7):
        current_date = dates[i]
        forecast_horizon = dates[i : i + 7]
        lookback_start = pd.Timestamp(current_date) - pd.Timedelta(days=28)

        fleet_lb = fleet_daily[
            (fleet_daily["dt"] >= lookback_start) & (fleet_daily["dt"] < current_date)
        ].copy()
        city_lb = df[
            (df["dt"] >= lookback_start) & (df["dt"] < current_date)
        ]

        if len(fleet_lb) < 28:
            continue

        fleet_avg_daily = fleet_lb["fleet_sales"].mean()
        fleet_lb["dow"] = fleet_lb["dt"].dt.dayofweek
        dow_means = fleet_lb.groupby("dow")["fleet_sales"].mean()
        dow_mults = dow_means / fleet_avg_daily

        total_fleet = fleet_lb["fleet_sales"].sum()
        city_shares = city_lb.groupby("city_id")["total_sales"].sum() / total_fleet

        for d in forecast_horizon:
            dow = pd.Timestamp(d).dayofweek
            fleet_forecast_d = fleet_avg_daily * dow_mults.get(dow, 1.0)
            for city_id in city_shares.index:
                forecasts.append({
                    "city_id": int(city_id),
                    "dt": pd.Timestamp(d).strftime("%Y-%m-%d"),
                    "forecast_sales": float(fleet_forecast_d * city_shares[city_id]),
                })

    return pd.DataFrame(forecasts) if forecasts else pd.DataFrame(
        columns=["city_id", "dt", "forecast_sales"]
    )


# ---------------------------------------------------------------------------
# Supabase push helpers
# ---------------------------------------------------------------------------


def _push_batch(
    client: Any,
    table: str,
    records: list[dict],
    on_conflict: str,
    batch_size: int = 500,
) -> int:
    total = 0
    for i in range(0, len(records), batch_size):
        batch = records[i : i + batch_size]
        client.table(table).upsert(batch, on_conflict=on_conflict).execute()
        total += len(batch)
    return total


def push_city_series(df: pd.DataFrame, client: Any = None) -> int:
    if client is None:
        client = make_supabase_client()
    records = []
    for row in df.itertuples(index=False):
        r = row._asdict()
        # Convert numpy scalars to Python natives
        rec = {
            k: (bool(v) if isinstance(v, (bool, np.bool_)) else
                int(v) if isinstance(v, (np.integer,)) else
                float(v) if isinstance(v, (np.floating,)) else
                v)
            for k, v in r.items()
        }
        records.append(rec)
    return _push_batch(client, "rca_city_series", records, "city_id,dt")


def push_city_hourly(df: pd.DataFrame, client: Any = None) -> int:
    if client is None:
        client = make_supabase_client()
    records = [
        {
            "city_id": int(r.city_id),
            "dt": str(r.dt),
            "hour": int(r.hour),
            "sales": float(r.sales) if r.sales is not None and not np.isnan(float(r.sales)) else None,
            "sales_share": float(r.sales_share) if r.sales_share is not None and not np.isnan(float(r.sales_share)) else None,
            "deviation_z": float(r.deviation_z) if r.deviation_z is not None and not np.isnan(float(r.deviation_z)) else None,
            "stockout_rate": float(r.stockout_rate) if r.stockout_rate is not None and not np.isnan(float(r.stockout_rate)) else None,
        }
        for r in df.itertuples(index=False)
    ]
    return _push_batch(client, "rca_city_hourly", records, "city_id,dt,hour")


def push_city_normals(df: pd.DataFrame, client: Any = None) -> int:
    if client is None:
        client = make_supabase_client()
    records = []
    for row in df.itertuples(index=False):
        records.append({
            "city_id": int(row.city_id),
            "density_tier": str(row.density_tier),
            "p25_sale": float(row.p25_sale) if row.p25_sale is not None else None,
            "p50_sale": float(row.p50_sale) if row.p50_sale is not None else None,
            "p75_sale": float(row.p75_sale) if row.p75_sale is not None else None,
            "avg_sale": float(row.avg_sale) if row.avg_sale is not None else None,
            "stddev_sale": float(row.stddev_sale) if row.stddev_sale is not None else None,
            "dow_pattern": row.dow_pattern if isinstance(row.dow_pattern, dict) else None,
        })
    _push_batch(client, "rca_city_normals", records, "city_id")
    return len(records)


def push_finance_forecast(df: pd.DataFrame, client: Any = None) -> int:
    if df.empty:
        return 0
    if client is None:
        client = make_supabase_client()
    records = [
        {
            "city_id": int(r.city_id),
            "dt": str(r.dt),
            "forecast_sales": float(r.forecast_sales),
        }
        for r in df.itertuples(index=False)
    ]
    return _push_batch(client, "rca_finance_forecast", records, "city_id,dt")


def push_city_segments(df: pd.DataFrame, client: Any = None) -> int:
    if df.empty:
        return 0
    if client is None:
        client = make_supabase_client()
    records = [
        {
            "city_id": int(r.city_id),
            "cluster_id": int(r.cluster_id) if r.cluster_id is not None else None,
            "segment_label": str(r.segment_label) if r.segment_label is not None else None,
        }
        for r in df.itertuples(index=False)
    ]
    _push_batch(client, "rca_city_segment", records, "city_id")
    return len(records)


def push_city_signal(df: pd.DataFrame, client: Any = None) -> int:
    """Upsert computed signal rows into rca_city_signal. Called by rca analyze."""
    if df.empty:
        return 0
    if client is None:
        client = make_supabase_client()

    float_cols = {
        "total_sales", "business_target", "target_deviation_pct",
        "previous_day_sales", "trailing_7d_avg_sales", "same_weekday_4w_avg_sales",
        "day_over_day_pct_change", "trailing_7d_pct_change", "same_weekday_4w_pct_change",
    }
    records = []
    for row in df.itertuples(index=False):
        r = row._asdict()
        rec: dict = {}
        for k, v in r.items():
            if k in float_cols:
                rec[k] = None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)
            elif isinstance(v, (np.integer,)):
                rec[k] = int(v)
            elif isinstance(v, (np.bool_,)):
                rec[k] = bool(v)
            else:
                rec[k] = v
        records.append(rec)
    return _push_batch(client, "rca_city_signal", records, "city_id,dt")


def push_city_correlations(df: pd.DataFrame, client: Any = None) -> int:
    if df.empty:
        return 0
    if client is None:
        client = make_supabase_client()
    records = [
        {
            "city_id": int(r.city_id),
            "corr_stockout": float(r.corr_stockout) if r.corr_stockout is not None else None,
            "corr_discount": float(r.corr_discount) if r.corr_discount is not None else None,
            "corr_activity": float(r.corr_activity) if r.corr_activity is not None else None,
            "corr_precpt": float(r.corr_precpt) if r.corr_precpt is not None else None,
            "corr_temperature": float(r.corr_temperature) if r.corr_temperature is not None else None,
        }
        for r in df.itertuples(index=False)
    ]
    _push_batch(client, "rca_city_correlations", records, "city_id")
    return len(records)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def ingest_to_supabase(raw_data_path: Path = RAW_DATA_PATH) -> dict[str, int]:
    """Full ETL: parquet → pandas aggregation → Supabase.

    Returns row counts per table pushed.
    """
    from rca.analytics import compute_city_segments, compute_driver_correlations, compute_intraday_profiles

    print("Loading raw parquet...")
    scoped = load_scoped_raw_data(raw_data_path)

    print("Building aggregated tables...")
    tables = build_all_tables(scoped)

    print("Building Supabase-shaped tables...")
    city_series_df = build_city_series_df(tables)
    city_normals_df = build_city_normals_df(tables)
    finance_forecast_df = build_finance_forecast_df(tables)

    print("Computing intraday profiles...")
    city_hourly_df = compute_intraday_profiles(
        tables["fact_sales_city_day"], tables["fact_stockout_city_day"]
    )

    print("Computing city segments...")
    segments_df = compute_city_segments(city_series_df)

    print("Computing driver correlations...")
    correlations_df = compute_driver_correlations(city_series_df)

    client = make_supabase_client()
    print("Pushing to Supabase...")

    counts: dict[str, int] = {}
    print("  rca_city_series...")
    counts["rca_city_series"] = push_city_series(city_series_df, client)
    print("  rca_city_hourly...")
    counts["rca_city_hourly"] = push_city_hourly(city_hourly_df, client)
    print("  rca_city_normals...")
    counts["rca_city_normals"] = push_city_normals(city_normals_df, client)
    print("  rca_finance_forecast...")
    counts["rca_finance_forecast"] = push_finance_forecast(finance_forecast_df, client)
    print("  rca_city_segment...")
    counts["rca_city_segment"] = push_city_segments(segments_df, client)
    print("  rca_city_correlations...")
    counts["rca_city_correlations"] = push_city_correlations(correlations_df, client)

    return counts


def validate_supabase_counts(expected_city_days: int = 1620) -> dict[str, int]:
    """Query Supabase and verify row counts for core tables."""
    client = make_supabase_client()
    counts: dict[str, int] = {}
    for table in ["rca_city_series", "rca_city_hourly", "rca_city_normals",
                  "rca_finance_forecast", "rca_city_segment", "rca_city_correlations",
                  "rca_city_signal"]:
        result = client.table(table).select("*", count="exact", head=True).execute()
        counts[table] = result.count or 0

    series_count = counts.get("rca_city_series", 0)
    if series_count != expected_city_days:
        print(f"  WARNING: rca_city_series has {series_count} rows, expected {expected_city_days}")
    else:
        print(f"  rca_city_series: {series_count} rows ✓")

    return counts
