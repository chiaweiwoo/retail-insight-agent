"""Context pack — factual grounding computed from Supabase, injected into every prompt.

Conservative rule: include ONLY things computed from the data.
Omit anything uncertain, do not interpret anonymized IDs, do not assign business meaning
to opaque integers unless empirically supported in the numbers.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rca.config import CONTEXT_PACK_PATH, DATE_START, DATE_END, SALES_FIELD_SEMANTICS, make_supabase_client


def build_context_pack(output_path: Path = CONTEXT_PACK_PATH) -> dict[str, Any]:
    """Compute factual grounding from Supabase and write context_pack.json + .md."""
    import pandas as pd

    client = make_supabase_client()

    resp = (
        client.table("rca_city_series")
        .select(
            "city_id,dt,total_sales,weekday,is_weekend,holiday_flag,"
            "holiday_name_inferred,holiday_note,density_tier"
        )
        .limit(2000)
        .execute()
    )
    series_df = pd.DataFrame(resp.data or [])
    if series_df.empty:
        raise RuntimeError("rca_city_series is empty. Run 'rca build' first.")

    series_df["dt"] = pd.to_datetime(series_df["dt"])
    series_df["total_sales"] = series_df["total_sales"].astype(float)

    city_count = int(series_df["city_id"].nunique())
    day_count = int(series_df["dt"].nunique())
    date_min = series_df["dt"].min().strftime("%Y-%m-%d")
    date_max = series_df["dt"].max().strftime("%Y-%m-%d")
    fleet_avg = round(float(series_df["total_sales"].mean()), 2)

    weekday_avg = (
        series_df.groupby("weekday")["total_sales"]
        .mean()
        .round(2)
        .to_dict()
    )
    weekday_pattern = {str(k): float(v) for k, v in weekday_avg.items()}

    weekend_avg = (
        series_df.groupby("is_weekend")["total_sales"]
        .mean()
        .round(2)
    )
    weekend_vs_weekday = {
        ("weekend" if k else "weekday"): float(v)
        for k, v in weekend_avg.items()
    }

    holiday_rows = series_df[series_df["holiday_flag"] == True][
        ["dt", "holiday_name_inferred", "holiday_note"]
    ].drop_duplicates("dt").sort_values("dt")
    holidays = [
        {
            "dt": row["dt"].strftime("%Y-%m-%d"),
            "name_inferred": str(row["holiday_name_inferred"] or ""),
            "note": str(row["holiday_note"] or ""),
        }
        for _, row in holiday_rows.iterrows()
    ]

    per_city_stats = (
        series_df.groupby("city_id")["total_sales"]
        .agg(["mean", "std", "min", "max"])
        .round(2)
        .reset_index()
    )
    per_city_rows = [
        {
            "city_id": int(row["city_id"]),
            "avg_daily_sales": float(row["mean"]),
            "stddev_daily_sales": float(row["std"]),
            "min_daily_sales": float(row["min"]),
            "max_daily_sales": float(row["max"]),
        }
        for _, row in per_city_stats.iterrows()
    ]

    if "density_tier" in series_df.columns and series_df["density_tier"].notna().any():
        tier_avg = (
            series_df.groupby("density_tier")["total_sales"]
            .mean()
            .round(2)
        )
        tier_empirical = {str(k): float(v) for k, v in tier_avg.items()}
    else:
        tier_empirical = {}

    pack: dict[str, Any] = {
        "dataset": {
            "source": "FreshRetailNet-50K (anonymized 2024 dataset)",
            "cities": city_count,
            "days": day_count,
            "date_min": date_min,
            "date_max": date_max,
            "granularity": "city-day",
            "note": (
                "City IDs (integers 0–17) and product IDs are opaque anonymized identifiers. "
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
        "density_tier_empirical": {
            "description": (
                "Average daily sales grouped by density tier (1 = >100 stores, 2 = 20-99, 3 = <20). "
                "Use as a weak prior for relative scale comparisons only."
            ),
            "by_tier": tier_empirical,
        },
        "per_city_normal": {str(row["city_id"]): row for row in per_city_rows},
        "holidays_in_window": holidays,
        "provenance": {
            "built_from": "Supabase rca_city_series",
            "limitations": [
                "No cost, margin, or product-category data available.",
                "No real-time or external data — this is a historical anonymized dataset.",
                "Treat all context as a weak prior, not ground truth.",
                f"The analysis window is fixed: {DATE_START} to {DATE_END}.",
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


def _get_city_segment_and_correlations(city_id: int) -> tuple[str | None, dict | None]:
    """Fetch segment label and top driver correlations for preamble enrichment."""
    try:
        client = make_supabase_client()
        seg_resp = (
            client.table("rca_city_segment")
            .select("segment_label")
            .eq("city_id", city_id)
            .limit(1)
            .execute()
        )
        segment_label = None
        if seg_resp.data:
            segment_label = str(seg_resp.data[0].get("segment_label") or "")

        corr_resp = (
            client.table("rca_city_correlations")
            .select("corr_stockout,corr_discount,corr_activity,corr_precpt,corr_temperature")
            .eq("city_id", city_id)
            .limit(1)
            .execute()
        )
        correlations = corr_resp.data[0] if corr_resp.data else None
        return segment_label, correlations
    except Exception:
        return None, None


def build_context_preamble(
    city_id: int,
    dt: str,
    pack: dict[str, Any] | None = None,
    profile_text: str | None = None,
) -> str:
    """Return a short grounding preamble for analyst/coordinator prompts.

    Keeps the preamble small — every byte here costs in every LLM call.
    Falls back to a minimal preamble if the pack is not available.
    profile_text: optional LLM-distilled episodic memory for this city.
    """
    if pack is None:
        pack = load_context_pack()

    segment_label, correlations = _get_city_segment_and_correlations(city_id)

    if pack is None:
        base = (
            "CONTEXT: Dataset is FreshRetailNet-50K, anonymized 2024 retail data. "
            "City IDs and product IDs are opaque — do not assume business meaning. "
            f"{SALES_FIELD_SEMANTICS} "
            f"Analysis date is {dt}; do not reference events after the data window.\n"
        )
        if segment_label:
            base += f"\nCity {city_id} segment: {segment_label}.\n"
        if profile_text:
            base += f"\nCITY MEMORY (city {city_id}) — treat as context, not ground truth:\n{profile_text}\n"
        return base

    dataset = pack["dataset"]
    fleet = pack["fleet"]
    city_normal = pack.get("per_city_normal", {}).get(str(city_id))

    lines = [
        "GROUNDING CONTEXT (factual, computed from data — treat as weak prior):",
        f"- Dataset: {dataset['source']}, {dataset['cities']} cities, {dataset['days']} days "
        f"({dataset['date_min']} to {dataset['date_max']}), city-day granularity.",
        "- City IDs (integers 0–17) and product IDs are opaque anonymized identifiers. "
        "Do not assign business meaning beyond what the numbers show.",
        f"- {SALES_FIELD_SEMANTICS}",
        f"- Fleet average daily sales: {fleet['avg_daily_sales']}.",
    ]

    if city_normal:
        lines.append(
            f"- City {city_id} normal: avg {city_normal['avg_daily_sales']} / day, "
            f"stddev {city_normal['stddev_daily_sales']} "
            f"(range {city_normal['min_daily_sales']}–{city_normal['max_daily_sales']})."
        )

    tier_data = pack.get("density_tier_empirical", {}).get("by_tier", {})
    if tier_data:
        tier_summary = ", ".join(f"tier {t}: avg {v}" for t, v in sorted(tier_data.items()))
        lines.append(
            f"- Density tier averages (1=>100 stores, 2=20-99, 3=<20): {tier_summary}. "
            "Use as a weak prior for relative scale only."
        )

    if segment_label:
        lines.append(f"- City {city_id} KMeans segment: {segment_label}.")

    if correlations:
        corr_parts = []
        for key, label in [
            ("corr_stockout", "stockout"),
            ("corr_discount", "discount"),
            ("corr_activity", "activity"),
            ("corr_precpt", "rainfall"),
            ("corr_temperature", "temperature"),
        ]:
            v = correlations.get(key)
            if v is not None:
                corr_parts.append(f"{label}={v:+.2f}")
        if corr_parts:
            lines.append(
                f"- City {city_id} driver correlations (sales vs): {', '.join(corr_parts)}. "
                "Sign indicates direction; treat as weak signal."
            )

    lines.append(
        "- No cost or margin data available. holiday_name_inferred values are uncertain priors."
    )
    lines.append(
        f"- Analysis date: {dt}. Do not reference events after the data window or invent company facts."
    )

    if profile_text:
        lines.append("")
        lines.append(
            f"CITY MEMORY (city {city_id}) — distilled from prior RCA runs, treat as context not ground truth:"
        )
        lines.append(profile_text)

    return "\n".join(lines) + "\n"


def _render_pack_md(pack: dict[str, Any]) -> str:
    ds = pack["dataset"]
    fl = pack["fleet"]
    lines = [
        "# Context Pack",
        "",
        f"**Source:** {ds['source']}",
        f"**Window:** {ds['date_min']} to {ds['date_max']} ({ds['cities']} cities, {ds['days']} days)",
        f"**Granularity:** {ds['granularity']}",
        "",
        "> " + ds["note"],
        "",
        "## Fleet",
        "",
        f"- Average daily sales (all cities, all days): **{fl['avg_daily_sales']}**",
        f"- Weekend vs weekday avg: {fl['weekend_vs_weekday_avg_sales']}",
        "",
        "## Density tier averages (empirical)",
        "",
        pack["density_tier_empirical"]["description"],
        "",
    ]
    for tier, avg in pack["density_tier_empirical"]["by_tier"].items():
        lines.append(f"- Tier {tier}: avg {avg} / day")
    lines += [
        "",
        "## Per-city normals",
        "",
        "| city_id | avg / day | stddev | min | max |",
        "| --- | --- | --- | --- | --- |",
    ]
    for city_id, s in pack["per_city_normal"].items():
        lines.append(
            f"| {city_id} | {s['avg_daily_sales']} | {s['stddev_daily_sales']} "
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
