from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE_PATH = PROJECT_ROOT / ".env"
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "train.parquet"
RAW_METADATA_PATH = PROJECT_ROOT / "data" / "raw" / "train_metadata.json"
DB_PATH = PROJECT_ROOT / "data" / "rca.duckdb"
LOG_DB_PATH = PROJECT_ROOT / "data" / "runs.duckdb"
ANALYSIS_PATH = PROJECT_ROOT / "data" / "analysis"
AGENT_BENCHMARK_PATH = ANALYSIS_PATH / "agent_benchmark_runs"
SCHEMA_PATH = PROJECT_ROOT / "rca" / "schema.sql"
# Keep old name as alias so existing code that references MIGRATION_PATH still works
MIGRATION_PATH = SCHEMA_PATH

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
SGT = timezone(timedelta(hours=8), name="SGT")


def load_env_file(env_file_path: Path = ENV_FILE_PATH) -> None:
    if not env_file_path.exists():
        return

    for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


load_env_file()


def current_timestamp_sgt_label() -> str:
    return datetime.now(SGT).strftime("%Y%m%dT%H%M%S_SGT")


def current_timestamp_sgt_iso() -> str:
    return datetime.now(SGT).isoformat(timespec="seconds")


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
