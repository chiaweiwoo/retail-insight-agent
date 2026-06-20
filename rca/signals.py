from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from rca.config import DB_PATH


MIN_BASELINE_OBSERVATIONS = 3


def load_sales_history(db_path: Path = DB_PATH) -> pd.DataFrame:
    if not db_path.exists():
        raise FileNotFoundError(f"DuckDB file is missing: {db_path}")

    connection = duckdb.connect(str(db_path), read_only=True)
    try:
        frame = connection.execute(
            """
            SELECT
                s.city_id,
                s.dt,
                s.total_sales,
                h.weekday,
                h.is_weekend,
                h.holiday_name_inferred
            FROM fact_sales_city_day AS s
            JOIN dim_holiday_day AS h USING (dt)
            ORDER BY s.city_id, s.dt
            """
        ).df()
    finally:
        connection.close()

    frame["dt"] = pd.to_datetime(frame["dt"])
    return frame


def _safe_pct_change(current: pd.Series, baseline: pd.Series) -> pd.Series:
    result = ((current - baseline) / baseline) * 100.0
    return result.where(baseline > 0)


def build_sales_signal_frame(frame: pd.DataFrame) -> pd.DataFrame:
    signals = frame.copy().sort_values(["city_id", "dt"]).reset_index(drop=True)

    by_city = signals.groupby("city_id", group_keys=False)
    signals["previous_day_sales"] = by_city["total_sales"].shift(1)
    signals["trailing_7d_avg_sales"] = by_city["total_sales"].transform(
        lambda series: series.shift(1).rolling(window=7, min_periods=MIN_BASELINE_OBSERVATIONS).mean()
    )

    by_city_weekday = signals.groupby(["city_id", "weekday"], group_keys=False)
    signals["same_weekday_4w_avg_sales"] = by_city_weekday["total_sales"].transform(
        lambda series: series.shift(1).rolling(window=4, min_periods=MIN_BASELINE_OBSERVATIONS).mean()
    )

    signals["day_over_day_abs_change"] = signals["total_sales"] - signals["previous_day_sales"]
    signals["day_over_day_pct_change"] = _safe_pct_change(
        signals["total_sales"], signals["previous_day_sales"]
    )

    signals["trailing_7d_abs_change"] = signals["total_sales"] - signals["trailing_7d_avg_sales"]
    signals["trailing_7d_pct_change"] = _safe_pct_change(
        signals["total_sales"], signals["trailing_7d_avg_sales"]
    )

    signals["same_weekday_4w_abs_change"] = (
        signals["total_sales"] - signals["same_weekday_4w_avg_sales"]
    )
    signals["same_weekday_4w_pct_change"] = _safe_pct_change(
        signals["total_sales"], signals["same_weekday_4w_avg_sales"]
    )

    signals["baseline_sales_floor"] = signals[
        ["previous_day_sales", "trailing_7d_avg_sales", "same_weekday_4w_avg_sales"]
    ].max(axis=1)

    return signals


def summarize_signal_distribution(signals: pd.DataFrame) -> dict[str, pd.DataFrame]:
    metric_columns = [
        "day_over_day_abs_change",
        "day_over_day_pct_change",
        "trailing_7d_abs_change",
        "trailing_7d_pct_change",
        "same_weekday_4w_abs_change",
        "same_weekday_4w_pct_change",
    ]

    distribution_rows: list[dict[str, float | str | int]] = []
    for metric in metric_columns:
        series = signals[metric].dropna()
        distribution_rows.append(
            {
                "metric": metric,
                "rows_with_baseline": int(series.shape[0]),
                "min": float(series.min()),
                "p10": float(series.quantile(0.10)),
                "p25": float(series.quantile(0.25)),
                "median": float(series.quantile(0.50)),
                "p75": float(series.quantile(0.75)),
                "p90": float(series.quantile(0.90)),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "std": float(series.std()),
            }
        )

    threshold_rows: list[dict[str, float | str | int]] = []
    pct_metrics = [
        "day_over_day_pct_change",
        "trailing_7d_pct_change",
        "same_weekday_4w_pct_change",
    ]
    pct_thresholds = [10, 15, 20, 25, 30]
    abs_thresholds = [10, 20, 30, 40, 50]

    for metric in pct_metrics:
        metric_series = signals[metric]
        abs_series = signals[metric.replace("_pct_", "_abs_")]
        baseline_floor = signals["baseline_sales_floor"]
        for pct_threshold in pct_thresholds:
            for abs_threshold in abs_thresholds:
                drop_mask = (
                    (metric_series <= -pct_threshold)
                    & (abs_series <= -abs_threshold)
                    & (baseline_floor >= abs_threshold)
                )
                lift_mask = (
                    (metric_series >= pct_threshold)
                    & (abs_series >= abs_threshold)
                    & (baseline_floor >= abs_threshold)
                )
                threshold_rows.append(
                    {
                        "metric": metric,
                        "pct_threshold": pct_threshold,
                        "abs_threshold": abs_threshold,
                        "drop_count": int(drop_mask.sum()),
                        "lift_count": int(lift_mask.sum()),
                        "trigger_count": int((drop_mask | lift_mask).sum()),
                    }
                )

    city_rows: list[dict[str, float | str | int]] = []
    for city_id, city_frame in signals.groupby("city_id"):
        city_rows.append(
            {
                "city_id": str(city_id),
                "avg_sales": float(city_frame["total_sales"].mean()),
                "sales_std": float(city_frame["total_sales"].std()),
                "day_over_day_pct_std": float(city_frame["day_over_day_pct_change"].dropna().std()),
                "trailing_7d_pct_std": float(city_frame["trailing_7d_pct_change"].dropna().std()),
                "same_weekday_4w_pct_std": float(
                    city_frame["same_weekday_4w_pct_change"].dropna().std()
                ),
            }
        )

    return {
        "distribution": pd.DataFrame(distribution_rows),
        "thresholds": pd.DataFrame(threshold_rows),
        "city_stability": pd.DataFrame(city_rows).sort_values("avg_sales", ascending=False),
    }


def summarize_pct_trigger_distribution(
    signals: pd.DataFrame,
    metric: str,
    thresholds: tuple[int, ...] = (10, 15, 20, 25, 30),
) -> dict[str, pd.DataFrame]:
    eligible = signals[signals[metric].notna()].copy()

    overall_rows: list[dict[str, float | str | int]] = []
    per_store_rows: list[dict[str, float | str | int]] = []
    per_date_rows: list[dict[str, float | str | int]] = []

    for pct_threshold in thresholds:
        drop_mask = eligible[metric] <= -pct_threshold
        lift_mask = eligible[metric] >= pct_threshold
        trigger_mask = drop_mask | lift_mask
        triggered = eligible[trigger_mask].copy()

        overall_rows.append(
            {
                "metric": metric,
                "pct_threshold": pct_threshold,
                "eligible_store_days": int(eligible.shape[0]),
                "triggered_store_days": int(trigger_mask.sum()),
                "drop_store_days": int(drop_mask.sum()),
                "lift_store_days": int(lift_mask.sum()),
                "triggered_dates": int(triggered["dt"].nunique()),
                "triggered_stores": int(triggered["city_id"].nunique()),
            }
        )

        for city_id, city_frame in eligible.groupby("city_id"):
            city_drop_mask = city_frame[metric] <= -pct_threshold
            city_lift_mask = city_frame[metric] >= pct_threshold
            city_trigger_count = int((city_drop_mask | city_lift_mask).sum())
            per_store_rows.append(
                {
                    "metric": metric,
                    "pct_threshold": pct_threshold,
                    "city_id": str(city_id),
                    "eligible_days": int(city_frame.shape[0]),
                    "drop_days": int(city_drop_mask.sum()),
                    "lift_days": int(city_lift_mask.sum()),
                    "triggered_days": city_trigger_count,
                    "trigger_rate_pct": float((city_trigger_count / city_frame.shape[0]) * 100.0),
                }
            )

        if not triggered.empty:
            per_date = (
                triggered.groupby("dt", as_index=False)
                .agg(triggered_store_days=("city_id", "count"))
                .sort_values(["triggered_store_days", "dt"], ascending=[False, True])
            )
            for row in per_date.itertuples(index=False):
                per_date_rows.append(
                    {
                        "metric": metric,
                        "pct_threshold": pct_threshold,
                        "dt": row.dt.strftime("%Y-%m-%d"),
                        "triggered_store_days": int(row.triggered_store_days),
                    }
                )

    return {
        "overall": pd.DataFrame(overall_rows),
        "per_store": pd.DataFrame(per_store_rows),
        "per_date": pd.DataFrame(per_date_rows),
    }


def build_pct_trigger_grid(
    signals: pd.DataFrame,
    metric: str,
    pct_threshold: int,
) -> pd.DataFrame:
    eligible = signals[signals[metric].notna()].copy()
    eligible["trigger_flag"] = "."
    eligible.loc[eligible[metric] <= -pct_threshold, "trigger_flag"] = "D"
    eligible.loc[eligible[metric] >= pct_threshold, "trigger_flag"] = "L"
    eligible["dt_label"] = eligible["dt"].dt.strftime("%Y-%m-%d")

    grid = eligible.pivot(
        index="city_id",
        columns="dt_label",
        values="trigger_flag",
    ).fillna(".")
    return grid.sort_index()


def recommend_primary_signal(summary_tables: dict[str, pd.DataFrame]) -> str:
    distribution = summary_tables["distribution"].set_index("metric")
    day_over_day = distribution.loc["day_over_day_pct_change"]
    trailing_7d = distribution.loc["trailing_7d_pct_change"]
    same_weekday = distribution.loc["same_weekday_4w_pct_change"]

    same_weekday_coverage_ratio = same_weekday["rows_with_baseline"] / day_over_day["rows_with_baseline"]
    same_weekday_bias = abs(same_weekday["mean"])

    if same_weekday_coverage_ratio >= 0.9 and same_weekday_bias <= 4.0:
        return "same_weekday_4w_pct_change"

    if trailing_7d["std"] < day_over_day["std"]:
        return "trailing_7d_pct_change"

    return "day_over_day_pct_change"
