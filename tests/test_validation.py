from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from rca_foundry.config import DB_PATH, EXPECTED_TABLE_ROWS
from rca_foundry.validation import (
    fetch_table_columns,
    table_exists,
    validate_database,
)


EXPECTED_SCHEMAS = {
    "dim_store": [("store_alias", "VARCHAR")],
    "dim_holiday_day": [
        ("dt", "DATE"),
        ("weekday", "VARCHAR"),
        ("is_weekend", "BOOLEAN"),
        ("holiday_flag", "BOOLEAN"),
        ("holiday_name_inferred", "VARCHAR"),
        ("holiday_note", "VARCHAR"),
    ],
    "dim_weather_day": [
        ("dt", "DATE"),
        ("precpt", "DOUBLE"),
        ("avg_temperature", "DOUBLE"),
        ("avg_humidity", "DOUBLE"),
        ("avg_wind_level", "DOUBLE"),
    ],
    "fact_discount_store_day": [
        ("store_alias", "VARCHAR"),
        ("dt", "DATE"),
        ("avg_discount", "DOUBLE"),
        ("discounted_product_rate", "DOUBLE"),
        ("deep_discount_product_rate", "DOUBLE"),
    ],
    "fact_activity_store_day": [
        ("store_alias", "VARCHAR"),
        ("dt", "DATE"),
        ("activity_product_rate", "DOUBLE"),
        ("activity_sales_share", "DOUBLE"),
    ],
}


@pytest.fixture(scope="module")
def connection() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        pytest.fail(f"Missing DuckDB file: {DB_PATH}")
    con = duckdb.connect(str(DB_PATH), read_only=True)
    yield con
    con.close()


def test_database_file_exists() -> None:
    assert DB_PATH.exists()


def test_required_tables_exist(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name in EXPECTED_TABLE_ROWS:
        assert table_exists(connection, table_name)


def test_expected_row_counts() -> None:
    assert validate_database() == EXPECTED_TABLE_ROWS


def test_selected_schemas_match(connection: duckdb.DuckDBPyConnection) -> None:
    for table_name, expected_schema in EXPECTED_SCHEMAS.items():
        assert fetch_table_columns(connection, table_name) == expected_schema


def test_preview_query_returns_single_row(connection: duckdb.DuckDBPyConnection) -> None:
    result = connection.execute(
        """
        SELECT COUNT(*), MIN(total_sales), MAX(total_sales)
        FROM fact_sales_store_day
        WHERE store_alias = 'h263' AND dt = DATE '2024-06-24'
        """
    ).fetchone()
    assert result == (1, pytest.approx(198.28), pytest.approx(198.28))


def test_validation_script_output() -> None:
    script_path = Path("scripts") / "validate_daily_tables.py"
    assert script_path.exists()
