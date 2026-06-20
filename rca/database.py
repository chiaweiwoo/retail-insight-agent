"""Build-time data ingestion: parquet -> city/date domain tables -> Supabase."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from rca.config import (
    ALL_TABLES,
    CITY_IDS,
    DATE_END,
    DATE_START,
    DEFAULT_DROP_THRESHOLD_PCT,
    DEFAULT_LIFT_THRESHOLD_PCT,
    EXPECTED_DAY_COUNT,
    HOURLY_LENGTH,
    RAW_DATA_PATH,
    REQUIRED_RAW_COLUMNS,
    TABLE_CALENDAR,
    TABLE_COMPLETIONS,
    TABLE_EVIDENCE_CACHE,
    TABLE_EVENTS,
    TABLE_EXTERNAL_EVENTS,
    TABLE_GOALS,
    TABLE_INVENTORY,
    TABLE_MEMORY,
    TABLE_OUTCOMES,
    TABLE_PRICING,
    TABLE_PROMOTIONS,
    TABLE_SALES,
    TABLE_SIGNALS,
    TABLE_WEATHER,
    current_timestamp_sgt_label,
    make_supabase_schema_client,
)


def _hour_columns(prefix: str) -> list[str]:
    return [f"hour_{hour:02d}_{prefix}" for hour in range(HOURLY_LENGTH)]


def _validate_required_columns(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_RAW_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Raw parquet is missing required columns: {missing}")


def _validate_hourly_lists(series: pd.Series, column_name: str) -> None:
    null_count = int(series.isna().sum())
    if null_count:
        raise ValueError(f"Column {column_name} contains {null_count} null hourly arrays.")
    bad_lengths = series.map(len).ne(HOURLY_LENGTH)
    if bool(bad_lengths.any()):
        raise ValueError(
            f"Column {column_name} contains {int(bad_lengths.sum())} malformed hourly arrays."
        )


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


def _expand_hourly_column(scoped: pd.DataFrame, source_column: str, output_suffix: str) -> pd.DataFrame:
    return pd.DataFrame(
        scoped[source_column].tolist(),
        columns=_hour_columns(output_suffix),
        index=scoped.index,
    ).astype(float)


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


def build_sales_df(scoped: pd.DataFrame) -> pd.DataFrame:
    sales = pd.concat(
        [
            scoped[["city_id", "dt", "store_id", "product_id", "sale_amount"]],
            _expand_hourly_column(scoped, "hours_sale", "sales"),
        ],
        axis=1,
    )
    return (
        sales.groupby(["city_id", "dt"], as_index=False)
        .agg(
            total_sales=("sale_amount", "sum"),
            store_count=("store_id", "nunique"),
            product_count=("product_id", "count"),
            active_product_count=("sale_amount", lambda s: int((s > 0).sum())),
            avg_sales_per_product=("sale_amount", "mean"),
            **{column: (column, "sum") for column in _hour_columns("sales")},
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
        .assign(dt=lambda df: df["dt"].dt.strftime("%Y-%m-%d"))
    )


def build_inventory_df(scoped: pd.DataFrame) -> pd.DataFrame:
    inventory = pd.concat(
        [
            scoped[["city_id", "dt", "stock_hour6_22_cnt"]],
            _expand_hourly_column(scoped, "hours_stock_status", "stockout_rate"),
        ],
        axis=1,
    )
    return (
        inventory.groupby(["city_id", "dt"], as_index=False)
        .agg(
            avg_stockout_hours=("stock_hour6_22_cnt", "mean"),
            stockout_product_count=("stock_hour6_22_cnt", lambda s: int((s > 0).sum())),
            severe_stockout_product_count=("stock_hour6_22_cnt", lambda s: int((s >= 8).sum())),
            full_stockout_product_count=("stock_hour6_22_cnt", lambda s: int((s == 16).sum())),
            stockout_product_rate=("stock_hour6_22_cnt", lambda s: float((s > 0).mean())),
            severe_stockout_product_rate=("stock_hour6_22_cnt", lambda s: float((s >= 8).mean())),
            full_stockout_product_rate=("stock_hour6_22_cnt", lambda s: float((s == 16).mean())),
            **{column: (column, "mean") for column in _hour_columns("stockout_rate")},
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
        .assign(dt=lambda df: df["dt"].dt.strftime("%Y-%m-%d"))
    )


def build_pricing_df(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped.groupby(["city_id", "dt"], as_index=False)
        .agg(
            avg_discount=("discount", "mean"),
            min_discount=("discount", "min"),
            discounted_product_count=("discount", lambda s: int((s < 0.999).sum())),
            discounted_product_rate=("discount", lambda s: float((s < 0.999).mean())),
            deep_discounted_product_count=("discount", lambda s: int((s < 0.5).sum())),
            deep_discounted_product_rate=("discount", lambda s: float((s < 0.5).mean())),
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
        .assign(dt=lambda df: pd.to_datetime(df["dt"]).dt.strftime("%Y-%m-%d"))
    )


def build_promotions_df(scoped: pd.DataFrame) -> pd.DataFrame:
    grouped = scoped.groupby(["city_id", "dt"], as_index=False)
    promotions = grouped.agg(
        activity_product_count=("activity_flag", "sum"),
        activity_product_rate=("activity_flag", "mean"),
        total_sales=("sale_amount", "sum"),
        activity_sales=(
            "sale_amount",
            lambda s: float(s[scoped.loc[s.index, "activity_flag"] == 1].sum()),
        ),
    )
    promotions["activity_sales_share"] = promotions.apply(
        lambda row: 0.0
        if row["total_sales"] == 0
        else float(row["activity_sales"] / row["total_sales"]),
        axis=1,
    )
    return (
        promotions.drop(columns=["total_sales"])
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
        .assign(dt=lambda df: pd.to_datetime(df["dt"]).dt.strftime("%Y-%m-%d"))
    )


def build_calendar_df(scoped: pd.DataFrame) -> pd.DataFrame:
    calendar = (
        scoped.groupby(["city_id", "dt"], as_index=False)
        .agg(holiday_flag=("holiday_flag", "max"))
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
    )
    calendar["weekday"] = calendar["dt"].dt.day_name().str.lower()
    calendar["is_weekend"] = calendar["dt"].dt.weekday >= 5
    calendar["holiday_flag"] = calendar["holiday_flag"].astype(bool)
    calendar["holiday_name_inferred"] = calendar["dt"].map(_infer_holiday_name)
    return calendar.assign(dt=lambda df: df["dt"].dt.strftime("%Y-%m-%d"))


def build_weather_df(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped.groupby(["city_id", "dt"], as_index=False)
        .agg(
            precpt=("precpt", "mean"),
            avg_temperature=("avg_temperature", "mean"),
            avg_humidity=("avg_humidity", "mean"),
            avg_wind_level=("avg_wind_level", "mean"),
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
        .assign(dt=lambda df: pd.to_datetime(df["dt"]).dt.strftime("%Y-%m-%d"))
    )


def build_goals_df(sales_df: pd.DataFrame) -> pd.DataFrame:
    df = sales_df[["city_id", "dt", "total_sales"]].copy()
    df["dt"] = pd.to_datetime(df["dt"])
    df = df.sort_values(["city_id", "dt"]).reset_index(drop=True)

    by_city = df.groupby("city_id", group_keys=False)
    df["recent_7d_avg_sales"] = by_city["total_sales"].transform(
        lambda s: s.shift(1).rolling(window=7, min_periods=3).mean()
    )
    by_city_dow = df.groupby(["city_id", df["dt"].dt.dayofweek], group_keys=False)
    df["same_weekday_4w_avg_sales"] = by_city_dow["total_sales"].transform(
        lambda s: s.shift(1).rolling(window=4, min_periods=3).mean()
    )
    df["expected_sales"] = df["same_weekday_4w_avg_sales"].fillna(df["recent_7d_avg_sales"])
    df["goal_method"] = np.where(
        df["same_weekday_4w_avg_sales"].notna(),
        "same_weekday_4w",
        np.where(df["recent_7d_avg_sales"].notna(), "recent_7d", "insufficient_history"),
    )
    return df.assign(dt=lambda frame: frame["dt"].dt.strftime("%Y-%m-%d"))[
        ["city_id", "dt", "expected_sales", "goal_method", "recent_7d_avg_sales", "same_weekday_4w_avg_sales"]
    ]


def build_signals_df(
    sales_df: pd.DataFrame,
    goals_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    build_version: str,
) -> pd.DataFrame:
    df = (
        sales_df[["city_id", "dt", "total_sales"]]
        .merge(goals_df, on=["city_id", "dt"], how="left")
        .merge(calendar_df[["city_id", "dt", "weekday", "holiday_name_inferred"]], on=["city_id", "dt"], how="left")
    )
    df["deviation_pct"] = (
        (df["total_sales"] - df["expected_sales"]) / df["expected_sales"] * 100.0
    ).where(df["expected_sales"] > 0)

    def label_row(row: pd.Series) -> str:
        if pd.isna(row["expected_sales"]):
            return "insufficient_history"
        if float(row["deviation_pct"]) <= DEFAULT_DROP_THRESHOLD_PCT:
            return "drop"
        if float(row["deviation_pct"]) >= DEFAULT_LIFT_THRESHOLD_PCT:
            return "lift"
        return "neutral"

    df["signal_label"] = df.apply(label_row, axis=1)
    df["build_version"] = build_version
    df["generated_at"] = build_version
    return df[
        [
            "city_id",
            "dt",
            "total_sales",
            "expected_sales",
            "deviation_pct",
            "goal_method",
            "signal_label",
            "weekday",
            "holiday_name_inferred",
            "build_version",
            "generated_at",
        ]
    ]


def _normalize_value(value: Any) -> Any:
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if np.isnan(value):
            return None
        return float(value)
    if pd.isna(value):
        return None
    return value


def _upsert_df(client: Any, table: str, df: pd.DataFrame, on_conflict: str, batch_size: int = 500) -> int:
    if df.empty:
        return 0
    records = []
    for row in df.itertuples(index=False):
        records.append({key: _normalize_value(value) for key, value in row._asdict().items()})
    total = 0
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        client.table(table).upsert(batch, on_conflict=on_conflict).execute()
        total += len(batch)
    return total


def reset_supabase_tables() -> None:
    client = make_supabase_schema_client()
    filters = {
        TABLE_SALES: ("city_id", 0),
        TABLE_INVENTORY: ("city_id", 0),
        TABLE_PRICING: ("city_id", 0),
        TABLE_PROMOTIONS: ("city_id", 0),
        TABLE_CALENDAR: ("city_id", 0),
        TABLE_WEATHER: ("city_id", 0),
        TABLE_GOALS: ("city_id", 0),
        TABLE_SIGNALS: ("city_id", 0),
        TABLE_OUTCOMES: ("city_id", 0),
        TABLE_EVENTS: ("id", 0),
        TABLE_COMPLETIONS: ("id", 0),
        TABLE_MEMORY: ("id", 0),
        TABLE_EVIDENCE_CACHE: ("id", 0),
        TABLE_EXTERNAL_EVENTS: ("id", 0),
    }
    for table in ALL_TABLES:
        column, cutoff = filters[table]
        client.table(table).delete().gte(column, cutoff).execute()


def ingest_to_supabase(raw_data_path: Path = RAW_DATA_PATH) -> dict[str, int]:
    print("Loading raw parquet...")
    scoped = load_scoped_raw_data(raw_data_path)
    build_version = current_timestamp_sgt_label()

    print("Building city/date domain tables...")
    sales_df = build_sales_df(scoped)
    inventory_df = build_inventory_df(scoped)
    pricing_df = build_pricing_df(scoped)
    promotions_df = build_promotions_df(scoped)
    calendar_df = build_calendar_df(scoped)
    weather_df = build_weather_df(scoped)
    goals_df = build_goals_df(sales_df)
    signals_df = build_signals_df(sales_df, goals_df, calendar_df, build_version)

    print("Resetting RCA schema tables...")
    reset_supabase_tables()

    client = make_supabase_schema_client()
    counts: dict[str, int] = {}
    counts[TABLE_SALES] = _upsert_df(client, TABLE_SALES, sales_df, "city_id,dt")
    counts[TABLE_INVENTORY] = _upsert_df(client, TABLE_INVENTORY, inventory_df, "city_id,dt")
    counts[TABLE_PRICING] = _upsert_df(client, TABLE_PRICING, pricing_df, "city_id,dt")
    counts[TABLE_PROMOTIONS] = _upsert_df(client, TABLE_PROMOTIONS, promotions_df, "city_id,dt")
    counts[TABLE_CALENDAR] = _upsert_df(client, TABLE_CALENDAR, calendar_df, "city_id,dt")
    counts[TABLE_WEATHER] = _upsert_df(client, TABLE_WEATHER, weather_df, "city_id,dt")
    counts[TABLE_GOALS] = _upsert_df(client, TABLE_GOALS, goals_df, "city_id,dt")
    counts[TABLE_SIGNALS] = _upsert_df(client, TABLE_SIGNALS, signals_df, "city_id,dt")
    return counts


def get_current_build_version() -> str | None:
    client = make_supabase_schema_client()
    result = client.table(TABLE_SIGNALS).select("build_version").limit(1).execute()
    rows = result.data or []
    if not rows:
        return None
    return str(rows[0].get("build_version") or "")
