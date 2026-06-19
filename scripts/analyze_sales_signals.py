from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from rca_foundry.signals import (
    build_sales_signal_frame,
    load_sales_history,
    recommend_primary_signal,
    summarize_signal_distribution,
)


def _write_markdown_summary(
    output_path: Path,
    recommended_metric: str,
    summary_tables,
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

    def as_markdown_table(frame) -> str:
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
        as_markdown_table(distribution),
        "",
        "## Threshold Grid Candidates",
        "",
        as_markdown_table(candidate_rows),
        "",
        "## Notes",
        "",
        "- `day_over_day` captures immediate swings but is the noisiest candidate.",
        "- `trailing_7d` is smoother and currently the best default operational trigger when we want broad coverage.",
        f"- `same_weekday_4w` is the most retail-shaped benchmark, but it only covers {same_weekday_coverage_ratio:.1%} of the rows that `day_over_day` covers in this 90-day slice.",
        f"- `same_weekday_4w` also has an upward mean drift of {same_weekday_bias:.2f}% in this sample, so it is better as a reasoning baseline than as the first trigger baseline.",
        "- Final RCA trigger logic should likely use both percentage change and absolute sales change.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    sales_history = load_sales_history()
    signals = build_sales_signal_frame(sales_history)
    summary_tables = summarize_signal_distribution(signals)
    recommended_metric = recommend_primary_signal(summary_tables)

    analysis_dir = PROJECT_ROOT / "data" / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = PROJECT_ROOT / "docs" / "analysis"
    docs_dir.mkdir(parents=True, exist_ok=True)

    signals_output_path = analysis_dir / "store_day_sales_signals.csv"
    distribution_output_path = analysis_dir / "signal_distribution_summary.csv"
    thresholds_output_path = analysis_dir / "signal_threshold_grid.csv"
    stability_output_path = analysis_dir / "store_signal_stability.csv"
    markdown_output_path = docs_dir / "sales_signal_distribution_summary.md"

    signals.to_csv(signals_output_path, index=False)
    summary_tables["distribution"].to_csv(distribution_output_path, index=False)
    summary_tables["thresholds"].to_csv(thresholds_output_path, index=False)
    summary_tables["store_stability"].to_csv(stability_output_path, index=False)
    _write_markdown_summary(markdown_output_path, recommended_metric, summary_tables)

    print(f"Sales signals exported: {signals_output_path}")
    print(f"Distribution summary exported: {distribution_output_path}")
    print(f"Threshold grid exported: {thresholds_output_path}")
    print(f"Store stability exported: {stability_output_path}")
    print(f"Markdown summary exported: {markdown_output_path}")
    print(f"Recommended primary signal candidate: {recommended_metric}")


if __name__ == "__main__":
    main()
