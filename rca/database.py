from __future__ import annotations

from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

from rca.config import (
    CITY_ID,
    DATE_END,
    DATE_START,
    DB_PATH,
    EXPECTED_DAY_COUNT,
    EXPECTED_STORE_COUNT,
    EXPECTED_STORE_DAY_COUNT,
    EXPECTED_TABLE_ROWS,
    FACT_TABLES,
    HOURLY_LENGTH,
    RAW_DATA_PATH,
    REQUIRED_RAW_COLUMNS,
    SCHEMA_PATH,
    STORE_MAP,
)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def rebuild_database(
    db_path: Path = DB_PATH,
    schema_path: Path = SCHEMA_PATH,
) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    connection = duckdb.connect(str(db_path))
    schema_sql = schema_path.read_text(encoding="utf-8")
    connection.execute(schema_sql)
    return connection


def connect_database(db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path), read_only=True)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def _hour_columns(prefix: str) -> list[str]:
    return [f"hour_{hour:02d}_{prefix}" for hour in range(HOURLY_LENGTH)]


def _validate_required_columns(frame: pd.DataFrame) -> None:
    missing_columns = sorted(REQUIRED_RAW_COLUMNS.difference(frame.columns))
    if missing_columns:
        raise ValueError(f"Raw parquet is missing required columns: {missing_columns}")


def _validate_hourly_lists(series: pd.Series, column_name: str) -> None:
    null_count = int(series.isna().sum())
    if null_count:
        raise ValueError(f"Column {column_name} contains {null_count} null hourly arrays.")

    bad_lengths = series.map(len).ne(HOURLY_LENGTH)
    if bool(bad_lengths.any()):
        bad_count = int(bad_lengths.sum())
        raise ValueError(
            f"Column {column_name} contains {bad_count} malformed hourly arrays. "
            f"Expected length {HOURLY_LENGTH}."
        )


def _validate_scope_counts(scoped: pd.DataFrame) -> None:
    store_count = int(scoped["store_alias"].nunique())
    day_count = int(scoped["dt"].nunique())
    store_day_count = int(scoped[["store_alias", "dt"]].drop_duplicates().shape[0])

    if store_count != EXPECTED_STORE_COUNT:
        raise ValueError(f"Expected {EXPECTED_STORE_COUNT} stores, found {store_count}.")
    if day_count != EXPECTED_DAY_COUNT:
        raise ValueError(f"Expected {EXPECTED_DAY_COUNT} dates, found {day_count}.")
    if store_day_count != EXPECTED_STORE_DAY_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_STORE_DAY_COUNT} store-day combinations, found {store_day_count}."
        )

    min_date = scoped["dt"].min().strftime("%Y-%m-%d")
    max_date = scoped["dt"].max().strftime("%Y-%m-%d")
    if min_date != DATE_START or max_date != DATE_END:
        raise ValueError(
            f"Expected date range {DATE_START} to {DATE_END}, found {min_date} to {max_date}."
        )


def _expand_hourly_column(
    scoped: pd.DataFrame,
    source_column: str,
    output_suffix: str,
) -> pd.DataFrame:
    expanded = pd.DataFrame(
        scoped[source_column].tolist(),
        columns=_hour_columns(output_suffix),
        index=scoped.index,
    )
    return expanded.astype(float)


def _infer_holiday_name(dt: pd.Timestamp) -> str:
    dt_string = dt.strftime("%Y-%m-%d")
    if "2024-04-04" <= dt_string <= "2024-04-06":
        return "qingming_period"
    if "2024-05-01" <= dt_string <= "2024-05-05":
        return "labor_day_period"
    if "2024-06-08" <= dt_string <= "2024-06-10":
        return "dragon_boat_period"
    if dt.weekday() >= 5:
        return "weekend"
    return "normal_weekday"


def load_scoped_raw_data(raw_data_path: Path = RAW_DATA_PATH) -> pd.DataFrame:
    if not raw_data_path.exists():
        raise FileNotFoundError(f"Raw parquet is missing: {raw_data_path}")

    frame = pd.read_parquet(raw_data_path)
    _validate_required_columns(frame)

    scoped = frame.loc[
        (frame["city_id"] == CITY_ID) & (frame["store_id"].isin(STORE_MAP.values()))
    ].copy()

    if scoped.empty:
        raise ValueError("Scoped raw data is empty after applying city/store filters.")

    scoped["dt"] = pd.to_datetime(scoped["dt"], format="%Y-%m-%d", errors="raise")
    _validate_hourly_lists(scoped["hours_sale"], "hours_sale")
    _validate_hourly_lists(scoped["hours_stock_status"], "hours_stock_status")

    store_lookup = {store_id: alias for alias, store_id in STORE_MAP.items()}
    scoped["store_alias"] = scoped["store_id"].map(store_lookup)

    if scoped["store_alias"].isna().any():
        raise ValueError("Store alias mapping failed for at least one scoped store_id.")

    _validate_scope_counts(scoped)
    return scoped


def build_dim_store(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped[["store_alias"]]
        .drop_duplicates()
        .sort_values("store_alias")
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
        [
            "dt",
            "weekday",
            "is_weekend",
            "holiday_flag",
            "holiday_name_inferred",
            "holiday_note",
        ]
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


def build_fact_sales_store_day(scoped: pd.DataFrame) -> pd.DataFrame:
    sales = pd.concat(
        [
            scoped[["store_alias", "dt", "product_id", "sale_amount"]],
            _expand_hourly_column(scoped, "hours_sale", "sales"),
        ],
        axis=1,
    )
    aggregated = (
        sales.groupby(["store_alias", "dt"], as_index=False)
        .agg(
            product_count=("product_id", "count"),
            active_product_count=("sale_amount", lambda series: int((series > 0).sum())),
            total_sales=("sale_amount", "sum"),
            avg_sales_per_product=("sale_amount", "mean"),
            **{column: (column, "sum") for column in _hour_columns("sales")},
        )
        .sort_values(["store_alias", "dt"])
        .reset_index(drop=True)
    )
    return aggregated


def build_fact_stockout_store_day(scoped: pd.DataFrame) -> pd.DataFrame:
    stockout = pd.concat(
        [
            scoped[["store_alias", "dt", "stock_hour6_22_cnt"]],
            _expand_hourly_column(scoped, "hours_stock_status", "stockout_rate"),
        ],
        axis=1,
    )
    aggregated = (
        stockout.groupby(["store_alias", "dt"], as_index=False)
        .agg(
            avg_stockout_hours=("stock_hour6_22_cnt", "mean"),
            stockout_product_rate=(
                "stock_hour6_22_cnt",
                lambda series: float((series > 0).mean()),
            ),
            severe_stockout_product_rate=(
                "stock_hour6_22_cnt",
                lambda series: float((series >= 8).mean()),
            ),
            full_stockout_product_rate=(
                "stock_hour6_22_cnt",
                lambda series: float((series == 16).mean()),
            ),
            **{column: (column, "mean") for column in _hour_columns("stockout_rate")},
        )
        .sort_values(["store_alias", "dt"])
        .reset_index(drop=True)
    )
    return aggregated


def build_fact_discount_store_day(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped.groupby(["store_alias", "dt"], as_index=False)
        .agg(
            avg_discount=("discount", "mean"),
            discounted_product_rate=(
                "discount",
                lambda series: float((series < 0.999).mean()),
            ),
            deep_discount_product_rate=(
                "discount",
                lambda series: float((series < 0.5).mean()),
            ),
        )
        .sort_values(["store_alias", "dt"])
        .reset_index(drop=True)
    )


def build_fact_activity_store_day(scoped: pd.DataFrame) -> pd.DataFrame:
    grouped = scoped.groupby(["store_alias", "dt"], as_index=False)
    activity = grouped.agg(
        activity_product_rate=("activity_flag", "mean"),
        total_sales=("sale_amount", "sum"),
        activity_sales=(
            "sale_amount",
            lambda series: float(
                series[scoped.loc[series.index, "activity_flag"] == 1].sum()
            ),
        ),
    )
    activity["activity_sales_share"] = activity.apply(
        lambda row: 0.0
        if row["total_sales"] == 0
        else float(row["activity_sales"] / row["total_sales"]),
        axis=1,
    )
    return (
        activity[["store_alias", "dt", "activity_product_rate", "activity_sales_share"]]
        .sort_values(["store_alias", "dt"])
        .reset_index(drop=True)
    )


def build_all_tables(scoped: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "dim_store": build_dim_store(scoped),
        "dim_holiday_day": build_dim_holiday_day(scoped),
        "dim_weather_day": build_dim_weather_day(scoped),
        "fact_sales_store_day": build_fact_sales_store_day(scoped),
        "fact_stockout_store_day": build_fact_stockout_store_day(scoped),
        "fact_discount_store_day": build_fact_discount_store_day(scoped),
        "fact_activity_store_day": build_fact_activity_store_day(scoped),
    }


def ingest_to_duckdb() -> dict[str, int]:
    scoped = load_scoped_raw_data()
    tables = build_all_tables(scoped)

    connection = rebuild_database()
    try:
        for table_name, table_frame in tables.items():
            connection.register("staging_table", table_frame)
            connection.execute(f"INSERT INTO {table_name} SELECT * FROM staging_table")
            connection.unregister("staging_table")

        row_counts = {
            table_name: int(
                connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            )
            for table_name in tables
        }
    finally:
        connection.close()

    return row_counts


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def table_exists(connection: duckdb.DuckDBPyConnection, table_name: str) -> bool:
    result = connection.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'main' AND table_name = ?
        """,
        [table_name],
    ).fetchone()
    return bool(result and result[0] == 1)


def fetch_table_columns(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
) -> list[tuple[str, str]]:
    result = connection.execute(f"DESCRIBE {table_name}").fetchall()
    return [(str(column_name), str(column_type)) for column_name, column_type, *_ in result]


def validate_row_counts(connection: duckdb.DuckDBPyConnection) -> dict[str, int]:
    row_counts: dict[str, int] = {}
    for table_name, expected_rows in EXPECTED_TABLE_ROWS.items():
        actual_rows = int(connection.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0])
        _assert(
            actual_rows == expected_rows,
            f"{table_name} row count mismatch: expected {expected_rows}, found {actual_rows}.",
        )
        row_counts[table_name] = actual_rows
    return row_counts


def validate_fact_shape(
    connection: duckdb.DuckDBPyConnection,
    table_name: str,
) -> None:
    result = connection.execute(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE store_alias IS NULL) AS null_store_alias,
            COUNT(*) FILTER (WHERE dt IS NULL) AS null_dt,
            COUNT(DISTINCT store_alias) AS distinct_stores,
            COUNT(DISTINCT dt) AS distinct_dates
        FROM {table_name}
        """
    ).fetchone()
    null_store_alias, null_dt, distinct_stores, distinct_dates = [int(value) for value in result]

    _assert(null_store_alias == 0, f"{table_name} contains null store_alias values.")
    _assert(null_dt == 0, f"{table_name} contains null dt values.")
    _assert(
        distinct_stores == EXPECTED_STORE_COUNT,
        f"{table_name} should contain {EXPECTED_STORE_COUNT} stores, found {distinct_stores}.",
    )
    _assert(
        distinct_dates == EXPECTED_DAY_COUNT,
        f"{table_name} should contain {EXPECTED_DAY_COUNT} dates, found {distinct_dates}.",
    )


def validate_rate_columns(connection: duckdb.DuckDBPyConnection) -> None:
    rate_tables = {
        "fact_stockout_store_day": [
            "stockout_product_rate",
            "severe_stockout_product_rate",
            "full_stockout_product_rate",
            *[f"hour_{hour:02d}_stockout_rate" for hour in range(24)],
        ],
        "fact_discount_store_day": [
            "discounted_product_rate",
            "deep_discount_product_rate",
        ],
        "fact_activity_store_day": [
            "activity_product_rate",
            "activity_sales_share",
        ],
    }

    for table_name, columns in rate_tables.items():
        expressions = ", ".join(
            [
                f"SUM(CASE WHEN {column} < 0 OR {column} > 1 THEN 1 ELSE 0 END) AS {column}"
                for column in columns
            ]
        )
        result = connection.execute(f"SELECT {expressions} FROM {table_name}").fetchone()
        for column_name, violation_count in zip(columns, result):
            _assert(
                int(violation_count) == 0,
                f"{table_name}.{column_name} contains values outside 0 to 1.",
            )


def validate_hourly_sales(connection: duckdb.DuckDBPyConnection) -> None:
    expressions = ", ".join(
        [
            f"SUM(CASE WHEN hour_{hour:02d}_sales < 0 THEN 1 ELSE 0 END) AS hour_{hour:02d}_sales"
            for hour in range(24)
        ]
    )
    result = connection.execute(f"SELECT {expressions} FROM fact_sales_store_day").fetchone()
    for hour, violation_count in enumerate(result):
        _assert(
            int(violation_count) == 0,
            f"fact_sales_store_day.hour_{hour:02d}_sales contains negative values.",
        )


def validate_required_tables(
    connection: duckdb.DuckDBPyConnection,
    table_names: Iterable[str] | None = None,
) -> None:
    tables = table_names or EXPECTED_TABLE_ROWS.keys()
    for table_name in tables:
        _assert(table_exists(connection, table_name), f"Missing required table: {table_name}")


def validate_daily_tables(db_path: Path = DB_PATH) -> dict[str, int]:
    _assert(db_path.exists(), f"DuckDB file is missing: {db_path}")

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        validate_required_tables(connection)
        row_counts = validate_row_counts(connection)

        for table_name in FACT_TABLES:
            validate_fact_shape(connection, table_name)

        validate_rate_columns(connection)
        validate_hourly_sales(connection)
    finally:
        connection.close()

    return row_counts


# Keep old name as alias for backward compat during transition
validate_database = validate_daily_tables
