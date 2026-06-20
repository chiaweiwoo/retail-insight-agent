"""Context pack — factual grounding computed once from the DB, injected into every prompt.

Conservative rule: include ONLY things computed from the data.
Omit anything uncertain, do not interpret anonymized IDs, do not assign business meaning
to opaque prefixes (h/m/l city IDes) unless empirically supported in the numbers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import duckdb

from rca.config import CONTEXT_PACK_PATH, DB_PATH, DATE_START, DATE_END, SALES_FIELD_SEMANTICS


def build_context_pack(db_path: Path = DB_PATH, output_path: Path = CONTEXT_PACK_PATH) -> dict[str, Any]:
    """Compute factual grounding from the DB and write context_pack.json + .md.

    All values are derived from the data. Nothing is asserted about anonymized IDs.
    """
    if not db_path.exists():
        raise RuntimeError(f"DB not found at {db_path}. Run 'rca build' first.")

    con = duckdb.connect(str(db_path), read_only=True)

    store_count = con.execute("SELECT COUNT(DISTINCT city_id) FROM fact_sales_city_day").fetchone()[0]
    day_count = con.execute("SELECT COUNT(DISTINCT dt) FROM fact_sales_city_day").fetchone()[0]
    date_min, date_max = con.execute(
        "SELECT MIN(CAST(dt AS VARCHAR)), MAX(CAST(dt AS VARCHAR)) FROM fact_sales_city_day"
    ).fetchone()

    per_store = con.execute("""
        SELECT
            city_id,
            ROUND(AVG(total_sales), 2) AS avg_daily_sales,
            ROUND(STDDEV(total_sales), 2) AS stddev_daily_sales,
            ROUND(MIN(total_sales), 2) AS min_daily_sales,
            ROUND(MAX(total_sales), 2) AS max_daily_sales
        FROM fact_sales_city_day
        GROUP BY city_id
        ORDER BY city_id
    """).fetchall()
    per_store_rows = [
        {
            "city_id": row[0],
            "avg_daily_sales": row[1],
            "stddev_daily_sales": row[2],
            "min_daily_sales": row[3],
            "max_daily_sales": row[4],
        }
        for row in per_store
    ]

    fleet_avg = con.execute("SELECT ROUND(AVG(total_sales), 2) FROM fact_sales_city_day").fetchone()[0]

    weekday_avg = con.execute("""
        SELECT h.weekday, ROUND(AVG(s.total_sales), 2) AS avg_sales
        FROM fact_sales_city_day AS s
        JOIN dim_holiday_day AS h USING (dt)
        GROUP BY h.weekday
        ORDER BY h.weekday
    """).fetchall()
    weekday_pattern = {str(row[0]): row[1] for row in weekday_avg}

    weekend_avg = con.execute("""
        SELECT h.is_weekend, ROUND(AVG(s.total_sales), 2) AS avg_sales
        FROM fact_sales_city_day AS s
        JOIN dim_holiday_day AS h USING (dt)
        GROUP BY h.is_weekend
        ORDER BY h.is_weekend
    """).fetchall()
    weekend_vs_weekday = {("weekend" if row[0] else "weekday"): row[1] for row in weekend_avg}

    holiday_days = con.execute("""
        SELECT CAST(dt AS VARCHAR), holiday_name_inferred, holiday_note
        FROM dim_holiday_day
        WHERE holiday_flag = 1
        ORDER BY dt
    """).fetchall()
    holidays = [
        {"dt": row[0], "name_inferred": row[1], "note": row[2]}
        for row in holiday_days
    ]

    # Empirical prefix grouping — stated as a computed observation, not a tier label
    prefix_avg = con.execute("""
        SELECT SUBSTRING(city_id, 1, 1) AS prefix, ROUND(AVG(total_sales), 2) AS avg_daily_sales
        FROM fact_sales_city_day
        GROUP BY prefix
        ORDER BY prefix
    """).fetchall()
    prefix_empirical = {row[0]: row[1] for row in prefix_avg}

    con.close()

    pack: dict[str, Any] = {
        "dataset": {
            "source": "FreshRetailNet-50K (anonymized 2024 dataset)",
            "stores": store_count,
            "days": day_count,
            "date_min": date_min,
            "date_max": date_max,
            "granularity": "store-day",
            "note": (
                "Store aliases, city IDs, and product IDs are opaque anonymized identifiers. "
                "Do not assign business meaning to them beyond what is computed from the data. "
                "holiday_name_inferred values are themselves inferred — treat as uncertain priors. "
                + SALES_FIELD_SEMANTICS
            ),
        },
        "fleet": {
            "avg_daily_sales": fleet_avg,
            "weekday_avg_sales": weekday_pattern,
            "weekend_vs_weekday_avg_sales": weekend_vs_weekday,
        },
        "store_prefix_empirical": {
            "description": (
                "Average daily sales grouped by the first letter of city_id. "
                "This is a computed grouping only — the prefix is an opaque identifier "
                "and is NOT labelled as a tier or size category."
            ),
            "by_prefix": prefix_empirical,
        },
        "per_store_normal": {row["city_id"]: row for row in per_store_rows},
        "holidays_in_window": holidays,
        "provenance": {
            "built_from": str(db_path),
            "limitations": [
                "No cost, margin, or product-category data available.",
                "No real-time or external data — this is a historical anonymized dataset.",
                "Treat all context as a weak prior, not ground truth.",
                "The analysis window is fixed: 2024-03-28 to 2024-06-25.",
                SALES_FIELD_SEMANTICS,
            ],
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(pack, indent=2, ensure_ascii=False), encoding="utf-8")

    md_path = output_path.with_suffix(".md")
    md_path.write_text(_render_pack_md(pack), encoding="utf-8")

    return pack


def load_context_pack(pack_path: Path = CONTEXT_PACK_PATH) -> dict[str, Any] | None:
    """Load the context pack from disk. Returns None if it has not been built yet."""
    if not pack_path.exists():
        return None
    return json.loads(pack_path.read_text(encoding="utf-8"))


def build_context_preamble(
    city_id: int,
    dt: str,
    pack: dict[str, Any] | None = None,
    profile_text: str | None = None,
) -> str:
    """Return a short grounding preamble for analyst/coordinator prompts.

    Keeps the preamble small — every byte here costs in every LLM call.
    Falls back to a minimal preamble if the pack is not available.
    profile_text: optional LLM-distilled episodic memory for this store.
    """
    if pack is None:
        pack = load_context_pack()

    if pack is None:
        base = (
            "CONTEXT: Dataset is FreshRetailNet-50K, anonymized 2024 retail data. "
            "Store aliases and product IDs are opaque — do not assume business meaning. "
            f"{SALES_FIELD_SEMANTICS} "
            f"Analysis date is {dt}; do not reference events after the data window.\n"
        )
        if profile_text:
            base += f"\nSTORE MEMORY ({city_id}) — treat as context, not ground truth:\n{profile_text}\n"
        return base

    dataset = pack["dataset"]
    fleet = pack["fleet"]
    store_normal = pack.get("per_store_normal", {}).get(city_id)

    lines = [
        f"GROUNDING CONTEXT (factual, computed from data — treat as weak prior):",
        f"- Dataset: {dataset['source']}, {dataset['stores']} stores, {dataset['days']} days "
        f"({dataset['date_min']} to {dataset['date_max']}), store-day granularity.",
        f"- Store aliases, city IDs, and product IDs are opaque anonymized identifiers. "
        f"Do not assign business meaning beyond what the numbers show.",
        f"- {SALES_FIELD_SEMANTICS}",
        f"- Fleet average daily sales: {fleet['avg_daily_sales']}.",
    ]

    if store_normal:
        lines.append(
            f"- {city_id} normal: avg {store_normal['avg_daily_sales']} / day, "
            f"stddev {store_normal['stddev_daily_sales']} "
            f"(range {store_normal['min_daily_sales']}–{store_normal['max_daily_sales']})."
        )

    prefix = city_id[0] if city_id else ""
    prefix_data = pack.get("store_prefix_empirical", {}).get("by_prefix", {})
    if prefix in prefix_data:
        lines.append(
            f"- Stores with '{prefix}' prefix average {prefix_data[prefix]} / day (computed grouping — "
            f"prefix is opaque, not a documented tier)."
        )

    lines.append(
        f"- No cost or margin data available. holiday_name_inferred values are uncertain priors."
    )
    lines.append(
        f"- Analysis date: {dt}. Do not reference events after the data window or invent company facts."
    )

    if profile_text:
        lines.append(f"")
        lines.append(f"STORE MEMORY ({city_id}) — distilled from prior RCA runs, treat as context not ground truth:")
        lines.append(profile_text)

    return "\n".join(lines) + "\n"


def _render_pack_md(pack: dict[str, Any]) -> str:
    ds = pack["dataset"]
    fl = pack["fleet"]
    lines = [
        "# Context Pack",
        "",
        f"**Source:** {ds['source']}",
        f"**Window:** {ds['date_min']} to {ds['date_max']} ({ds['stores']} stores, {ds['days']} days)",
        f"**Granularity:** {ds['granularity']}",
        "",
        "> " + ds["note"],
        "",
        "## Fleet",
        "",
        f"- Average daily sales (all stores, all days): **{fl['avg_daily_sales']}**",
        f"- Weekend vs weekday avg: {fl['weekend_vs_weekday_avg_sales']}",
        "",
        "## Store prefix groupings (empirical, not tier labels)",
        "",
        pack["store_prefix_empirical"]["description"],
        "",
    ]
    for prefix, avg in pack["store_prefix_empirical"]["by_prefix"].items():
        lines.append(f"- `{prefix}` prefix: avg {avg} / day")
    lines += [
        "",
        "## Per-store normals",
        "",
        "| store | avg / day | stddev | min | max |",
        "| --- | --- | --- | --- | --- |",
    ]
    for alias, s in pack["per_store_normal"].items():
        lines.append(
            f"| {alias} | {s['avg_daily_sales']} | {s['stddev_daily_sales']} "
            f"| {s['min_daily_sales']} | {s['max_daily_sales']} |"
        )
    lines += [
        "",
        "## Holidays in window (inferred — uncertain)",
        "",
    ]
    for h in pack.get("holidays_in_window", []):
        lines.append(f"- {h['dt']}: {h['name_inferred']} ({h['note']})")
    lines += [
        "",
        "## Limitations",
        "",
    ]
    for lim in pack["provenance"]["limitations"]:
        lines.append(f"- {lim}")
    return "\n".join(lines) + "\n"
