from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from rca.config import DB_PATH


EVIDENCE_SELECT = """
    SELECT
        s.city_id,
        CAST(s.dt AS VARCHAR) AS dt,
        s.product_count,
        s.active_product_count,
        s.total_sales,
        s.avg_sales_per_product,
        s.hour_00_sales, s.hour_01_sales, s.hour_02_sales, s.hour_03_sales,
        s.hour_04_sales, s.hour_05_sales, s.hour_06_sales, s.hour_07_sales,
        s.hour_08_sales, s.hour_09_sales, s.hour_10_sales, s.hour_11_sales,
        s.hour_12_sales, s.hour_13_sales, s.hour_14_sales, s.hour_15_sales,
        s.hour_16_sales, s.hour_17_sales, s.hour_18_sales, s.hour_19_sales,
        s.hour_20_sales, s.hour_21_sales, s.hour_22_sales, s.hour_23_sales,
        st.avg_stockout_hours,
        st.stockout_product_rate,
        st.severe_stockout_product_rate,
        st.full_stockout_product_rate,
        st.hour_00_stockout_rate, st.hour_01_stockout_rate, st.hour_02_stockout_rate, st.hour_03_stockout_rate,
        st.hour_04_stockout_rate, st.hour_05_stockout_rate, st.hour_06_stockout_rate, st.hour_07_stockout_rate,
        st.hour_08_stockout_rate, st.hour_09_stockout_rate, st.hour_10_stockout_rate, st.hour_11_stockout_rate,
        st.hour_12_stockout_rate, st.hour_13_stockout_rate, st.hour_14_stockout_rate, st.hour_15_stockout_rate,
        st.hour_16_stockout_rate, st.hour_17_stockout_rate, st.hour_18_stockout_rate, st.hour_19_stockout_rate,
        st.hour_20_stockout_rate, st.hour_21_stockout_rate, st.hour_22_stockout_rate, st.hour_23_stockout_rate,
        d.avg_discount,
        d.discounted_product_rate,
        d.deep_discount_product_rate,
        a.activity_product_rate,
        a.activity_sales_share,
        h.weekday,
        h.is_weekend,
        h.holiday_flag,
        h.holiday_name_inferred,
        h.holiday_note,
        w.precpt,
        w.avg_temperature,
        w.avg_humidity,
        w.avg_wind_level
    FROM fact_sales_city_day AS s
    JOIN fact_stockout_city_day AS st USING (city_id, dt)
    JOIN fact_discount_city_day AS d USING (city_id, dt)
    JOIN fact_activity_city_day AS a USING (city_id, dt)
    JOIN dim_holiday_day AS h USING (dt)
    JOIN dim_weather_day AS w USING (dt)
"""


def _connect(db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB file is missing: {db_path}")
    return duckdb.connect(str(db_path), read_only=True)


def list_city_ides(db_path: Path = DB_PATH) -> list[str]:
    connection = _connect(db_path)
    try:
        result = connection.execute(
            "SELECT city_id FROM dim_city ORDER BY city_id"
        ).fetchall()
        return [str(row[0]) for row in result]
    finally:
        connection.close()


def list_dates(db_path: Path = DB_PATH) -> list[str]:
    connection = _connect(db_path)
    try:
        result = connection.execute(
            "SELECT CAST(dt AS VARCHAR) FROM dim_holiday_day ORDER BY dt"
        ).fetchall()
        return [str(row[0]) for row in result]
    finally:
        connection.close()


def _assert_store_and_date_exist(
    connection: duckdb.DuckDBPyConnection,
    city_id: int,
    dt: str,
) -> None:
    store_exists = connection.execute(
        "SELECT COUNT(*) FROM dim_city WHERE city_id = ?",
        [city_id],
    ).fetchone()[0]
    if int(store_exists) != 1:
        raise ValueError(f"Unknown city_id: {city_id}")

    date_exists = connection.execute(
        "SELECT COUNT(*) FROM dim_holiday_day WHERE dt = CAST(? AS DATE)",
        [dt],
    ).fetchone()[0]
    if int(date_exists) != 1:
        raise ValueError(f"Unknown date: {dt}")


def get_store_day_evidence(
    city_id: int,
    dt: str,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    connection = _connect(db_path)
    try:
        _assert_store_and_date_exist(connection, city_id, dt)
        result = connection.execute(
            EVIDENCE_SELECT
            + """
            WHERE s.city_id = ?
              AND s.dt = CAST(? AS DATE)
            """,
            [city_id, dt],
        ).fetchone()
        if result is None:
            raise ValueError(f"No evidence found for city_id={city_id} dt={dt}")

        sales = [float(value) for value in result[6:30]]
        stockout_rates = [float(value) for value in result[34:58]]

        return {
            "city_id": str(result[0]),
            "dt": str(result[1]),
            "sales": {
                "product_count": int(result[2]),
                "active_product_count": int(result[3]),
                "total_sales": float(result[4]),
                "avg_sales_per_product": float(result[5]),
                "hourly_sales": sales,
            },
            "stockout": {
                "avg_stockout_hours": float(result[30]),
                "stockout_product_rate": float(result[31]),
                "severe_stockout_product_rate": float(result[32]),
                "full_stockout_product_rate": float(result[33]),
                "hourly_stockout_rate": stockout_rates,
            },
            "discount": {
                "avg_discount": float(result[58]),
                "discounted_product_rate": float(result[59]),
                "deep_discount_product_rate": float(result[60]),
            },
            "activity": {
                "activity_product_rate": float(result[61]),
                "activity_sales_share": float(result[62]),
            },
            "holiday": {
                "weekday": str(result[63]),
                "is_weekend": bool(result[64]),
                "holiday_flag": bool(result[65]),
                "holiday_name_inferred": str(result[66]),
                "holiday_note": str(result[67]),
            },
            "weather": {
                "precpt": float(result[68]),
                "avg_temperature": float(result[69]),
                "avg_humidity": float(result[70]),
                "avg_wind_level": float(result[71]),
            },
        }
    finally:
        connection.close()


def fetch_all_evidence_records(db_path: Path = DB_PATH) -> list[dict[str, Any]]:
    connection = _connect(db_path)
    try:
        rows = connection.execute(
            EVIDENCE_SELECT + " ORDER BY s.city_id, s.dt"
        ).fetchall()
        records: list[dict[str, Any]] = []
        for row in rows:
            sales = [float(value) for value in row[6:30]]
            stockout_rates = [float(value) for value in row[34:58]]
            records.append(
                {
                    "city_id": str(row[0]),
                    "dt": str(row[1]),
                    "sales": {
                        "product_count": int(row[2]),
                        "active_product_count": int(row[3]),
                        "total_sales": float(row[4]),
                        "avg_sales_per_product": float(row[5]),
                        "hourly_sales": sales,
                    },
                    "stockout": {
                        "avg_stockout_hours": float(row[30]),
                        "stockout_product_rate": float(row[31]),
                        "severe_stockout_product_rate": float(row[32]),
                        "full_stockout_product_rate": float(row[33]),
                        "hourly_stockout_rate": stockout_rates,
                    },
                    "discount": {
                        "avg_discount": float(row[58]),
                        "discounted_product_rate": float(row[59]),
                        "deep_discount_product_rate": float(row[60]),
                    },
                    "activity": {
                        "activity_product_rate": float(row[61]),
                        "activity_sales_share": float(row[62]),
                    },
                    "holiday": {
                        "weekday": str(row[63]),
                        "is_weekend": bool(row[64]),
                        "holiday_flag": bool(row[65]),
                        "holiday_name_inferred": str(row[66]),
                        "holiday_note": str(row[67]),
                    },
                    "weather": {
                        "precpt": float(row[68]),
                        "avg_temperature": float(row[69]),
                        "avg_humidity": float(row[70]),
                        "avg_wind_level": float(row[71]),
                    },
                }
            )
        return records
    finally:
        connection.close()


def export_evidence_dataset(
    output_path: Path,
    db_path: Path = DB_PATH,
) -> Path:
    stores = list_city_ides(db_path)
    dates = list_dates(db_path)
    records = fetch_all_evidence_records(db_path)

    payload = {
        "stores": stores,
        "dates": dates,
        "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
