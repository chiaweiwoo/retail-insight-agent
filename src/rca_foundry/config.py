from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "train.parquet"
RAW_METADATA_PATH = PROJECT_ROOT / "data" / "raw" / "train_metadata.json"
DB_PATH = PROJECT_ROOT / "data" / "db" / "rca_foundry.duckdb"
MIGRATION_PATH = PROJECT_ROOT / "sql" / "migrations" / "001_create_daily_tables.sql"

DATE_START = "2024-03-28"
DATE_END = "2024-06-25"
EXPECTED_DAY_COUNT = 90
EXPECTED_STORE_COUNT = 15
EXPECTED_STORE_DAY_COUNT = 1350
CITY_ID = 0
HOURLY_LENGTH = 24

STORE_MAP = {
    "h235": 235,
    "h263": 263,
    "h182": 182,
    "h018": 18,
    "h555": 555,
    "m679": 679,
    "m648": 648,
    "m041": 41,
    "m236": 236,
    "m386": 386,
    "l260": 260,
    "l185": 185,
    "l165": 165,
    "l164": 164,
    "l175": 175,
}

EXPECTED_TABLE_ROWS = {
    "dim_store": EXPECTED_STORE_COUNT,
    "dim_holiday_day": EXPECTED_DAY_COUNT,
    "dim_weather_day": EXPECTED_DAY_COUNT,
    "fact_sales_store_day": EXPECTED_STORE_DAY_COUNT,
    "fact_stockout_store_day": EXPECTED_STORE_DAY_COUNT,
    "fact_discount_store_day": EXPECTED_STORE_DAY_COUNT,
    "fact_activity_store_day": EXPECTED_STORE_DAY_COUNT,
}

REQUIRED_RAW_COLUMNS = {
    "city_id",
    "store_id",
    "product_id",
    "dt",
    "sale_amount",
    "hours_sale",
    "stock_hour6_22_cnt",
    "hours_stock_status",
    "discount",
    "holiday_flag",
    "activity_flag",
    "precpt",
    "avg_temperature",
    "avg_humidity",
    "avg_wind_level",
}

FACT_TABLES = [
    "fact_sales_store_day",
    "fact_stockout_store_day",
    "fact_discount_store_day",
    "fact_activity_store_day",
]

DEFAULT_SIGNAL_METRIC = "trailing_7d_pct_change"
DEFAULT_DROP_THRESHOLD_PCT = -20.0
DEFAULT_LIFT_THRESHOLD_PCT = 30.0

DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
DEFAULT_LLM_MAX_TOOL_ROUNDS = 8


def get_llm_api_key() -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing API key. Set DEEPSEEK_API_KEY (preferred) or OPENAI_API_KEY."
        )
    return api_key


def get_llm_base_url() -> str:
    return os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL)


def get_llm_model() -> str:
    return os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL)


def get_llm_thinking_enabled() -> bool:
    value = os.getenv("DEEPSEEK_THINKING", "false").strip().lower()
    return value in {"1", "true", "yes", "on"}
