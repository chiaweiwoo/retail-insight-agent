from __future__ import annotations

from pathlib import Path
from typing import Iterable

import duckdb
import pandas as pd

from rca.config import (
    CITY_IDS,
    DATE_END,
    DATE_START,
    DB_PATH,
    EXPECTED_DAY_COUNT,
    EXPECTED_TABLE_ROWS,
    FACT_TABLES,
    HOURLY_LENGTH,
    RAW_DATA_PATH,
    REQUIRED_RAW_COLUMNS,
    SCHEMA_PATH,
    make_supabase_client,
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

    scoped = frame.loc[frame["city_id"].isin(CITY_IDS)].copy()

    if scoped.empty:
        raise ValueError("Scoped raw data is empty.")

    scoped["dt"] = pd.to_datetime(scoped["dt"], format="%Y-%m-%d", errors="raise")
    _validate_hourly_lists(scoped["hours_sale"], "hours_sale")
    _validate_hourly_lists(scoped["hours_stock_status"], "hours_stock_status")

    _validate_scope_counts(scoped)
    return scoped


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


def build_fact_sales_city_day(scoped: pd.DataFrame) -> pd.DataFrame:
    sales = pd.concat(
        [
            scoped[["city_id", "dt", "product_id", "sale_amount"]],
            _expand_hourly_column(scoped, "hours_sale", "sales"),
        ],
        axis=1,
    )
    aggregated = (
        sales.groupby(["city_id", "dt"], as_index=False)
        .agg(
            product_count=("product_id", "count"),
            active_product_count=("sale_amount", lambda series: int((series > 0).sum())),
            total_sales=("sale_amount", "sum"),
            avg_sales_per_product=("sale_amount", "mean"),
            **{column: (column, "sum") for column in _hour_columns("sales")},
        )
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
    )
    return aggregated


def build_fact_stockout_city_day(scoped: pd.DataFrame) -> pd.DataFrame:
    stockout = pd.concat(
        [
            scoped[["city_id", "dt", "stock_hour6_22_cnt"]],
            _expand_hourly_column(scoped, "hours_stock_status", "stockout_rate"),
        ],
        axis=1,
    )
    aggregated = (
        stockout.groupby(["city_id", "dt"], as_index=False)
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
        .sort_values(["city_id", "dt"])
        .reset_index(drop=True)
    )
    return aggregated


def build_fact_discount_city_day(scoped: pd.DataFrame) -> pd.DataFrame:
    return (
        scoped.groupby(["city_id", "dt"], as_index=False)
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


def run_analytics(db_path: Path = DB_PATH) -> dict[str, int]:
    """Run the analytics pipeline (STL, intraday, segments, correlations) on local DuckDB."""
    from rca.analytics import run_analytics_pipeline
    return run_analytics_pipeline(db_path)


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
            COUNT(*) FILTER (WHERE city_id IS NULL) AS null_city_id,
            COUNT(*) FILTER (WHERE dt IS NULL) AS null_dt,
            COUNT(DISTINCT city_id) AS distinct_cities,
            COUNT(DISTINCT dt) AS distinct_dates
        FROM {table_name}
        """
    ).fetchone()
    null_city_id, null_dt, distinct_cities, distinct_dates = [int(value) for value in result]

    _assert(null_city_id == 0, f"{table_name} contains null city_id values.")
    _assert(null_dt == 0, f"{table_name} contains null dt values.")
    _assert(
        distinct_dates == EXPECTED_DAY_COUNT,
        f"{table_name} should contain {EXPECTED_DAY_COUNT} dates, found {distinct_dates}.",
    )
    _assert(distinct_cities > 0, f"{table_name} contains zero cities.")


def validate_rate_columns(connection: duckdb.DuckDBPyConnection) -> None:
    rate_tables = {
        "fact_stockout_city_day": [
            "stockout_product_rate",
            "severe_stockout_product_rate",
            "full_stockout_product_rate",
            *_hour_columns("stockout_rate"),
        ],
        "fact_discount_city_day": [
            "discounted_product_rate",
            "deep_discount_product_rate",
        ],
        "fact_activity_city_day": [
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
        f"MIN(hour_{hour:02d}_sales) AS min_h{hour:02d}" for hour in range(HOURLY_LENGTH)
    )
    result = connection.execute(f"SELECT {expressions} FROM fact_sales_city_day").fetchone()
    for hour, min_val in enumerate(result):
        _assert(
            float(min_val) >= 0,
            f"fact_sales_city_day.hour_{hour:02d}_sales contains negative values.",
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


# ---------------------------------------------------------------------------
# Supabase sync
# ---------------------------------------------------------------------------


def _city_tier(store_count: int) -> str:
    """Return density tier: 1 (>100), 2 (20-99), 3 (<20)."""
    if store_count >= 100:
        return "1"
    if store_count >= 20:
        return "2"
    return "3"


def sync_series_to_supabase(db_path: Path = DB_PATH, batch_size: int = 500) -> int:
    """Push daily city aggregates from local DuckDB → Supabase city_series.

    Returns total rows upserted.
    """
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT
                c.city_id,
                dc.store_count,
                CAST(c.dt AS VARCHAR) AS dt,
                c.total_sales,
                c.product_count,
                c.active_product_count,
                c.avg_sales_per_product,
                st.stockout_product_rate,
                st.severe_stockout_product_rate,
                d.avg_discount,
                d.discounted_product_rate,
                a.activity_product_rate,
                a.activity_sales_share,
                h.holiday_flag,
                h.is_weekend,
                h.weekday
            FROM fact_sales_city_day c
            JOIN dim_city dc USING (city_id)
            JOIN fact_stockout_city_day st USING (city_id, dt)
            JOIN fact_discount_city_day d USING (city_id, dt)
            JOIN fact_activity_city_day a USING (city_id, dt)
            JOIN dim_holiday_day h USING (dt)
            ORDER BY c.city_id, c.dt
            """
        ).fetchall()
    finally:
        connection.close()

    if not rows:
        return 0

    client = make_supabase_client()
    total = 0
    batch = []
    for row in rows:
        city_id = int(row[0])
        store_count = int(row[1])
        batch.append({
            "city_id": city_id,
            "density_tier": _city_tier(store_count),
            "dt": str(row[2]),
            "total_sales": float(row[3]) if row[3] is not None else None,
            "product_count": int(row[4]) if row[4] is not None else None,
            "active_product_count": int(row[5]) if row[5] is not None else None,
            "avg_sales_per_product": float(row[6]) if row[6] is not None else None,
            "stockout_product_rate": float(row[7]) if row[7] is not None else None,
            "severe_stockout_rate": float(row[8]) if row[8] is not None else None,
            "avg_discount": float(row[9]) if row[9] is not None else None,
            "discounted_product_rate": float(row[10]) if row[10] is not None else None,
            "activity_product_rate": float(row[11]) if row[11] is not None else None,
            "activity_sales_share": float(row[12]) if row[12] is not None else None,
            "holiday_flag": bool(row[13]) if row[13] is not None else None,
            "is_weekend": bool(row[14]) if row[14] is not None else None,
            "weekday": str(row[15]) if row[15] is not None else None,
        })
        if len(batch) >= batch_size:
            client.table("rca_city_series").upsert(
                batch, on_conflict="city_id,dt"
            ).execute()
            total += len(batch)
            batch = []

    if batch:
        client.table("rca_city_series").upsert(
            batch, on_conflict="city_id,dt"
        ).execute()
        total += len(batch)

    return total


def sync_normals_to_supabase(db_path: Path = DB_PATH) -> int:
    """Compute per-city baselines and upsert to Supabase city_normals."""
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = connection.execute(
            """
            SELECT
                c.city_id,
                dc.store_count,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY c.total_sales) AS p25,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY c.total_sales) AS p50,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY c.total_sales) AS p75,
                AVG(c.total_sales) AS avg_sale,
                STDDEV(c.total_sales) AS stddev_sale
            FROM fact_sales_city_day c
            JOIN dim_city dc USING (city_id)
            GROUP BY c.city_id, dc.store_count
            """
        ).fetchall()

        # Weekday pattern per city: avg sales by day-of-week, normalised to fleet mean=1
        dow_rows = connection.execute(
            """
            SELECT
                c.city_id,
                DAYOFWEEK(c.dt) - 1 AS dow,
                AVG(c.total_sales) AS dow_avg
            FROM fact_sales_city_day c
            GROUP BY c.city_id, DAYOFWEEK(c.dt)
            ORDER BY c.city_id, dow
            """
        ).fetchall()
    finally:
        connection.close()

    import json

    dow_map: dict[str, dict[str, float]] = {}
    for city_id_val, dow, avg in dow_rows:
        dow_map.setdefault(str(city_id_val), {})[str(int(dow))] = float(avg) if avg else 0.0

    client = make_supabase_client()
    records = []
    for row in rows:
        city_id = int(row[0])
        store_count = int(row[1])
        records.append({
            "city_id": city_id,
            "density_tier": _city_tier(store_count),
            "p25_sale": float(row[2]) if row[2] is not None else None,
            "p50_sale": float(row[3]) if row[3] is not None else None,
            "p75_sale": float(row[4]) if row[4] is not None else None,
            "avg_sale": float(row[5]) if row[5] is not None else None,
            "stddev_sale": float(row[6]) if row[6] is not None else None,
            "dow_pattern": dow_map.get(str(city_id)),
        })

    if records:
        client.table("rca_city_normals").upsert(
            records, on_conflict="city_id"
        ).execute()

    return len(records)


def sync_analytics_to_supabase(db_path: Path = DB_PATH, batch_size: int = 500) -> dict[str, int]:
    """Push analytics tables from local DuckDB → Supabase rca_city_* analytics tables."""
    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        signal_rows = connection.execute(
            "SELECT city_id, CAST(dt AS VARCHAR), stl_residual, residual_zscore, signal_label "
            "FROM analytics_city_signal ORDER BY city_id, dt"
        ).fetchall()

        hourly_rows = connection.execute(
            "SELECT city_id, CAST(dt AS VARCHAR), hour, sales, sales_share, deviation_z, stockout_rate "
            "FROM analytics_city_hourly ORDER BY city_id, dt, hour"
        ).fetchall()

        segment_rows = connection.execute(
            "SELECT city_id, cluster_id, segment_label FROM analytics_city_segment ORDER BY city_id"
        ).fetchall()

        corr_rows = connection.execute(
            "SELECT city_id, corr_stockout, corr_discount, corr_activity, corr_precpt, corr_temperature "
            "FROM analytics_city_correlations ORDER BY city_id"
        ).fetchall()
    finally:
        connection.close()

    client = make_supabase_client()
    totals: dict[str, int] = {}

    # --- rca_city_signal ---
    batch: list[dict] = []
    total = 0
    for r in signal_rows:
        batch.append({
            "city_id": int(r[0]),
            "dt": str(r[1]),
            "stl_residual": float(r[2]) if r[2] is not None else None,
            "residual_zscore": float(r[3]) if r[3] is not None else None,
            "signal_label": str(r[4]) if r[4] is not None else None,
        })
        if len(batch) >= batch_size:
            client.table("rca_city_signal").upsert(batch, on_conflict="city_id,dt").execute()
            total += len(batch)
            batch = []
    if batch:
        client.table("rca_city_signal").upsert(batch, on_conflict="city_id,dt").execute()
        total += len(batch)
    totals["rca_city_signal"] = total

    # --- rca_city_hourly ---
    batch = []
    total = 0
    for r in hourly_rows:
        batch.append({
            "city_id": int(r[0]),
            "dt": str(r[1]),
            "hour": int(r[2]),
            "sales": float(r[3]) if r[3] is not None else None,
            "sales_share": float(r[4]) if r[4] is not None else None,
            "deviation_z": float(r[5]) if r[5] is not None else None,
            "stockout_rate": float(r[6]) if r[6] is not None else None,
        })
        if len(batch) >= batch_size:
            client.table("rca_city_hourly").upsert(batch, on_conflict="city_id,dt,hour").execute()
            total += len(batch)
            batch = []
    if batch:
        client.table("rca_city_hourly").upsert(batch, on_conflict="city_id,dt,hour").execute()
        total += len(batch)
    totals["rca_city_hourly"] = total

    # --- rca_city_segment ---
    records = [
        {"city_id": int(r[0]), "cluster_id": int(r[1]) if r[1] is not None else None, "segment_label": str(r[2]) if r[2] is not None else None}
        for r in segment_rows
    ]
    if records:
        client.table("rca_city_segment").upsert(records, on_conflict="city_id").execute()
    totals["rca_city_segment"] = len(records)

    # --- rca_city_correlations ---
    records = [
        {
            "city_id": int(r[0]),
            "corr_stockout": float(r[1]) if r[1] is not None else None,
            "corr_discount": float(r[2]) if r[2] is not None else None,
            "corr_activity": float(r[3]) if r[3] is not None else None,
            "corr_precpt": float(r[4]) if r[4] is not None else None,
            "corr_temperature": float(r[5]) if r[5] is not None else None,
        }
        for r in corr_rows
    ]
    if records:
        client.table("rca_city_correlations").upsert(records, on_conflict="city_id").execute()
    totals["rca_city_correlations"] = len(records)

    return totals
