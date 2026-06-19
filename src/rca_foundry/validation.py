from __future__ import annotations

from typing import Iterable

import duckdb

from rca_foundry.config import (
    DB_PATH,
    EXPECTED_DAY_COUNT,
    EXPECTED_STORE_COUNT,
    EXPECTED_TABLE_ROWS,
    FACT_TABLES,
)


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


def validate_database(db_path=DB_PATH) -> dict[str, int]:
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
