from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE_PATH = PROJECT_ROOT / ".env"
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "train.parquet"
RAW_METADATA_PATH = PROJECT_ROOT / "data" / "raw" / "train_metadata.json"
DOCS_PATH = PROJECT_ROOT / "docs"
AGENT_SKILLS_PATH = PROJECT_ROOT / "rca" / "agent_skills"

RCA_SCHEMA = "rca"

DATE_START = "2024-03-28"
DATE_END = "2024-06-25"
EXPECTED_DAY_COUNT = 90
HOURLY_LENGTH = 24
CITY_IDS = list(range(18))

REQUIRED_RAW_COLUMNS = {
    "city_id",
    "store_id",
    "management_group_id",
    "first_category_id",
    "second_category_id",
    "third_category_id",
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

TABLE_SALES = "sales"
TABLE_INVENTORY = "inventory"
TABLE_PRICING = "pricing"
TABLE_PROMOTIONS = "promotions"
TABLE_CALENDAR = "calendar"
TABLE_WEATHER = "weather"
TABLE_GOALS = "goals"
TABLE_SIGNALS = "signals"
TABLE_OUTCOMES = "outcomes"
TABLE_EVENTS = "events"
TABLE_COMPLETIONS = "completions"
TABLE_MEMORY = "memory"
TABLE_EVIDENCE_CACHE = "evidence_cache"
TABLE_EXTERNAL_EVENTS = "external_events"
TABLE_REPLAY_REVIEW = "replay_review"

ALL_TABLES = [
    TABLE_SALES,
    TABLE_INVENTORY,
    TABLE_PRICING,
    TABLE_PROMOTIONS,
    TABLE_CALENDAR,
    TABLE_WEATHER,
    TABLE_GOALS,
    TABLE_SIGNALS,
    TABLE_OUTCOMES,
    TABLE_EVENTS,
    TABLE_COMPLETIONS,
    TABLE_MEMORY,
    TABLE_EVIDENCE_CACHE,
    TABLE_EXTERNAL_EVENTS,
    TABLE_REPLAY_REVIEW,
]

SALES_FIELD_SEMANTICS = (
    "sale_amount and hours_sale are normalized sales amounts from the source dataset. "
    "Treat them as relative sales amounts for comparison, not currency and not literal units."
)

ACTIVITY_FIELD_SEMANTICS = (
    "activity_flag is an unlabeled internal activity indicator. It may represent a promotion "
    "or commercial push, but its exact business meaning is unknown."
)

HOLIDAY_FIELD_SEMANTICS = (
    "holiday_flag marks a holiday-like date, but the name itself must be inferred from date context "
    "or external search and should always be labeled as inferred."
)

DEFAULT_DROP_THRESHOLD_PCT = -10.0
DEFAULT_LIFT_THRESHOLD_PCT = 25.0
RCA_MAX_INVESTIGATION_ROUNDS = 5
DEFAULT_LLM_BASE_URL = "https://api.deepseek.com"
DEFAULT_LLM_MODEL = "deepseek-v4-flash"
DEFAULT_LLM_MAX_TOOL_ROUNDS = 6
DEFAULT_NEWS_RESULTS = 5
SGT = timezone(timedelta(hours=8), name="SGT")


def load_env_file(env_file_path: Path = ENV_FILE_PATH) -> None:
    if not env_file_path.exists():
        return
    for raw_line in env_file_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


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
    return os.getenv("DEEPSEEK_THINKING", "false").strip().lower() in {"1", "true", "yes", "on"}


def get_research_enabled() -> bool:
    return os.getenv("RCA_RESEARCH_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def get_max_investigation_rounds() -> int:
    return int(os.getenv("RCA_MAX_INVESTIGATION_ROUNDS", str(RCA_MAX_INVESTIGATION_ROUNDS)))


def get_stat_tools_enabled() -> bool:
    return os.getenv("RCA_STAT_TOOLS_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def get_llm_judge_enabled() -> bool:
    return os.getenv("RCA_LLM_JUDGE_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def get_model_fast() -> str:
    return os.getenv("DEEPSEEK_MODEL_FAST", "deepseek-v4-flash")


def get_model_deep() -> str:
    return os.getenv("DEEPSEEK_MODEL_DEEP", "deepseek-v4-pro")


def get_supabase_url() -> str:
    url = os.getenv("SUPABASE_URL", "")
    if not url:
        raise RuntimeError("SUPABASE_URL is not set. Fill it in from your Supabase project settings.")
    return url


def get_supabase_service_key() -> str:
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not key:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is not set.")
    return key


def get_supabase_anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "")


def make_supabase_client():
    from supabase._sync.client import create_client

    return create_client(get_supabase_url(), get_supabase_service_key())


def make_supabase_schema_client(schema: str = RCA_SCHEMA):
    return make_supabase_client().schema(schema)


def load_raw_metadata() -> dict[str, Any]:
    if not RAW_METADATA_PATH.exists():
        return {}
    return json.loads(RAW_METADATA_PATH.read_text(encoding="utf-8"))
