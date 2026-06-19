from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from rca_foundry.signals import (
    build_pct_trigger_grid,
    build_sales_signal_frame,
    load_sales_history,
    recommend_primary_signal,
    summarize_pct_trigger_distribution,
    summarize_signal_distribution,
)


def as_markdown_table(frame) -> str:
    headers = ["index", *list(frame.columns)] if frame.index.name or True else list(frame.columns)
    rows = [headers, ["---"] * len(headers)]
    for index, row in zip(frame.index, frame.itertuples(index=False, name=None)):
        rows.append([str(index), *[str(value) for value in row]])
    return "\n".join("| " + " | ".join(row) + " |" for row in rows)


def _write_markdown_summary(
    output_path: Path,
    recommended_metric: str,
    summary_tables,
    pct_trigger_tables,
) -> None:
    distribution = summary_tables["distribution"]
    thresholds = summary_tables["thresholds"]

    best_threshold_rows = (
        thresholds.loc[thresholds["metric"] == recommended_metric]
        .sort_values(["trigger_count", "pct_threshold", "abs_threshold"])
        .reset_index(drop=True)
    )
    moderate_band = best_threshold_rows[
        (best_threshold_rows["trigger_count"] >= 60)
        & (best_threshold_rows["trigger_count"] <= 240)
    ]
    candidate_rows = moderate_band.head(5) if not moderate_band.empty else best_threshold_rows.head(5)
    distribution_lookup = distribution.set_index("metric")
    same_weekday_coverage_ratio = (
        distribution_lookup.loc["same_weekday_4w_pct_change", "rows_with_baseline"]
        / distribution_lookup.loc["day_over_day_pct_change", "rows_with_baseline"]
    )
    same_weekday_bias = distribution_lookup.loc["same_weekday_4w_pct_change", "mean"]
    trigger_overall = pct_trigger_tables["overall"]
    anomaly_candidate = trigger_overall.loc[
        trigger_overall["pct_threshold"] == 25
    ].iloc[0]
    discussion_candidate = trigger_overall.loc[
        trigger_overall["pct_threshold"] == 20
    ].iloc[0]
    store_spread = (
        pct_trigger_tables["per_store"]
        .loc[pct_trigger_tables["per_store"]["pct_threshold"] == 20, ["store_alias", "triggered_days", "trigger_rate_pct"]]
        .sort_values(["triggered_days", "store_alias"], ascending=[False, True])
        .head(8)
    )

    def as_markdown_value_table(frame) -> str:
        headers = list(frame.columns)
        rows = [headers, ["---"] * len(headers)]
        for row in frame.itertuples(index=False, name=None):
            rows.append([str(value) for value in row])
        return "\n".join("| " + " | ".join(row) + " |" for row in rows)

    lines = [
        "# Sales Signal Distribution Summary",
        "",
        f"Recommended primary signal candidate: `{recommended_metric}`",
        "",
        "## Distribution Snapshot",
        "",
        as_markdown_value_table(distribution),
        "",
        "## Threshold Grid Candidates",
        "",
        as_markdown_value_table(candidate_rows),
        "",
        "## Pure Percent Trigger Distribution",
        "",
        as_markdown_value_table(trigger_overall),
        "",
        "## Per-Store Spread At 20%",
        "",
        as_markdown_value_table(store_spread),
        "",
        "## Grid Legend",
        "",
        "- `D` = drop trigger",
        "- `L` = lift trigger",
        "- `.` = no trigger",
        "",
        "## Notes",
        "",
        "- `day_over_day` captures immediate swings but is the noisiest candidate.",
        "- `trailing_7d` is smoother and currently the best default operational trigger when we want broad coverage.",
        f"- `same_weekday_4w` is the most retail-shaped benchmark, but it only covers {same_weekday_coverage_ratio:.1%} of the rows that `day_over_day` covers in this 90-day slice.",
        f"- `same_weekday_4w` also has an upward mean drift of {same_weekday_bias:.2f}% in this sample, so it is better as a reasoning baseline than as the first trigger baseline.",
        f"- Pure `trailing_7d_pct_change` at 20% gives {int(discussion_candidate['triggered_store_days'])} triggered store-days across {int(discussion_candidate['triggered_dates'])} calendar dates.",
        f"- Pure `trailing_7d_pct_change` at 25% gives {int(anomaly_candidate['triggered_store_days'])} triggered store-days across {int(anomaly_candidate['triggered_dates'])} calendar dates, which is a better anomaly-style discussion set.",
        "- The current trigger exploration is per store-day, not a single global daily alarm.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    sales_history = load_sales_history()
    signals = build_sales_signal_frame(sales_history)
    summary_tables = summarize_signal_distribution(signals)
    pct_trigger_tables = summarize_pct_trigger_distribution(
        signals,
        metric="trailing_7d_pct_change",
    )
    recommended_metric = recommend_primary_signal(summary_tables)

    analysis_dir = PROJECT_ROOT / "data" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = PROJECT_ROOT / "docs" / "analysis"
    docs_dir.mkdir(parents=True, exist_ok=True)

    signals_output_path = analysis_dir / "store_day_sales_signals.csv"
    distribution_output_path = analysis_dir / "signal_distribution_summary.csv"
    thresholds_output_path = analysis_dir / "signal_threshold_grid.csv"
    stability_output_path = analysis_dir / "store_signal_stability.csv"
    pct_overall_output_path = analysis_dir / "pct_trigger_overall_summary.csv"
    pct_store_output_path = analysis_dir / "pct_trigger_by_store.csv"
    pct_date_output_path = analysis_dir / "pct_trigger_by_date.csv"
    grid_dir = analysis_dir / "trigger_grids"
    grid_docs_dir = docs_dir / "trigger_grids"
    markdown_output_path = docs_dir / "sales_signal_distribution_summary.md"

    grid_dir.mkdir(parents=True, exist_ok=True)
    grid_docs_dir.mkdir(parents=True, exist_ok=True)

    signals.to_csv(signals_output_path, index=False)
    summary_tables["distribution"].to_csv(distribution_output_path, index=False)
    summary_tables["thresholds"].to_csv(thresholds_output_path, index=False)
    summary_tables["store_stability"].to_csv(stability_output_path, index=False)
    pct_trigger_tables["overall"].to_csv(pct_overall_output_path, index=False)
    pct_trigger_tables["per_store"].to_csv(pct_store_output_path, index=False)
    pct_trigger_tables["per_date"].to_csv(pct_date_output_path, index=False)

    for pct_threshold in (20, 25, 30):
        grid = build_pct_trigger_grid(
            signals,
            metric="trailing_7d_pct_change",
            pct_threshold=pct_threshold,
        )
        active_grid = grid.loc[:, (grid != ".").any(axis=0)]
        grid_csv_path = grid_dir / f"trailing_7d_pct_trigger_grid_{pct_threshold}.csv"
        grid_md_path = grid_docs_dir / f"trailing_7d_pct_trigger_grid_{pct_threshold}.md"
        active_grid_csv_path = (
            grid_dir / f"trailing_7d_pct_trigger_grid_{pct_threshold}_active_only.csv"
        )
        active_grid_md_path = (
            grid_docs_dir / f"trailing_7d_pct_trigger_grid_{pct_threshold}_active_only.md"
        )
        grid.to_csv(grid_csv_path)
        active_grid.to_csv(active_grid_csv_path)
        grid_md_path.write_text(as_markdown_table(grid), encoding="utf-8")
        active_grid_md_path.write_text(as_markdown_table(active_grid), encoding="utf-8")

    _write_markdown_summary(
        markdown_output_path,
        recommended_metric,
        summary_tables,
        pct_trigger_tables,
    )

    print(f"Sales signals exported: {signals_output_path}")
    print(f"Distribution summary exported: {distribution_output_path}")
    print(f"Threshold grid exported: {thresholds_output_path}")
    print(f"Store stability exported: {stability_output_path}")
    print(f"Percent trigger overall summary exported: {pct_overall_output_path}")
    print(f"Percent trigger by-store summary exported: {pct_store_output_path}")
    print(f"Percent trigger by-date summary exported: {pct_date_output_path}")
    print(f"Trigger grids exported: {grid_dir}")
    print(f"Markdown summary exported: {markdown_output_path}")
    print(f"Recommended primary signal candidate: {recommended_metric}")


if __name__ == "__main__":
    main()
