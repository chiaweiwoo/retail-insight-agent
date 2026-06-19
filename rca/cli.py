from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_build(args: argparse.Namespace) -> None:
    from rca.database import ingest_to_duckdb, validate_daily_tables
    from rca.config import DB_PATH

    print("Building database...")
    row_counts = ingest_to_duckdb()
    for table, count in row_counts.items():
        print(f"  {table}: {count} rows")

    print("Validating...")
    validate_daily_tables()
    print(f"Database built and validated: {DB_PATH}")


def _cmd_analyze(args: argparse.Namespace) -> None:
    from rca.signals import (
        build_pct_trigger_grid,
        build_sales_signal_frame,
        load_sales_history,
        recommend_primary_signal,
        summarize_pct_trigger_distribution,
        summarize_signal_distribution,
    )
    from rca.config import ANALYSIS_PATH, PROJECT_ROOT

    def _as_markdown_table(frame) -> str:
        headers = ["index", *list(frame.columns)]
        rows = [headers, ["---"] * len(headers)]
        for index, row in zip(frame.index, frame.itertuples(index=False, name=None)):
            rows.append([str(index), *[str(value) for value in row]])
        return "\n".join("| " + " | ".join(row) + " |" for row in rows)

    def _as_markdown_value_table(frame) -> str:
        headers = list(frame.columns)
        rows = [headers, ["---"] * len(headers)]
        for row in frame.itertuples(index=False, name=None):
            rows.append([str(value) for value in row])
        return "\n".join("| " + " | ".join(row) + " |" for row in rows)

    def _write_markdown_summary(output_path, recommended_metric, summary_tables, pct_trigger_tables):
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
        anomaly_candidate = trigger_overall.loc[trigger_overall["pct_threshold"] == 25].iloc[0]
        discussion_candidate = trigger_overall.loc[trigger_overall["pct_threshold"] == 20].iloc[0]
        store_spread = (
            pct_trigger_tables["per_store"]
            .loc[
                pct_trigger_tables["per_store"]["pct_threshold"] == 20,
                ["store_alias", "triggered_days", "trigger_rate_pct"],
            ]
            .sort_values(["triggered_days", "store_alias"], ascending=[False, True])
            .head(8)
        )

        lines = [
            "# Sales Signal Distribution Summary",
            "",
            f"Recommended primary signal candidate: `{recommended_metric}`",
            "",
            "## Distribution Snapshot",
            "",
            _as_markdown_value_table(distribution),
            "",
            "## Threshold Grid Candidates",
            "",
            _as_markdown_value_table(candidate_rows),
            "",
            "## Pure Percent Trigger Distribution",
            "",
            _as_markdown_value_table(trigger_overall),
            "",
            "## Per-Store Spread At 20%",
            "",
            _as_markdown_value_table(store_spread),
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

    sales_history = load_sales_history()
    signals = build_sales_signal_frame(sales_history)
    summary_tables = summarize_signal_distribution(signals)
    pct_trigger_tables = summarize_pct_trigger_distribution(
        signals,
        metric="trailing_7d_pct_change",
    )
    recommended_metric = recommend_primary_signal(summary_tables)

    analysis_dir = ANALYSIS_PATH
    analysis_dir.mkdir(parents=True, exist_ok=True)
    docs_dir = PROJECT_ROOT / "docs" / "analysis"
    docs_dir.mkdir(parents=True, exist_ok=True)

    signals.to_csv(analysis_dir / "store_day_sales_signals.csv", index=False)
    summary_tables["distribution"].to_csv(analysis_dir / "signal_distribution_summary.csv", index=False)
    summary_tables["thresholds"].to_csv(analysis_dir / "signal_threshold_grid.csv", index=False)
    summary_tables["store_stability"].to_csv(analysis_dir / "store_signal_stability.csv", index=False)
    pct_trigger_tables["overall"].to_csv(analysis_dir / "pct_trigger_overall_summary.csv", index=False)
    pct_trigger_tables["per_store"].to_csv(analysis_dir / "pct_trigger_by_store.csv", index=False)
    pct_trigger_tables["per_date"].to_csv(analysis_dir / "pct_trigger_by_date.csv", index=False)

    grid_dir = analysis_dir / "trigger_grids"
    grid_dir.mkdir(parents=True, exist_ok=True)

    for pct_threshold in (20, 25, 30):
        grid = build_pct_trigger_grid(
            signals,
            metric="trailing_7d_pct_change",
            pct_threshold=pct_threshold,
        )
        active_grid = grid.loc[:, (grid != ".").any(axis=0)]
        grid.to_csv(grid_dir / f"trailing_7d_pct_trigger_grid_{pct_threshold}.csv")
        active_grid.to_csv(grid_dir / f"trailing_7d_pct_trigger_grid_{pct_threshold}_active_only.csv")

    _write_markdown_summary(
        docs_dir / "sales_signal_distribution_summary.md",
        recommended_metric,
        summary_tables,
        pct_trigger_tables,
    )

    print(f"Signals exported to {analysis_dir}")
    print(f"Recommended primary signal: {recommended_metric}")


def _cmd_run(args: argparse.Namespace) -> None:
    from rca.agents import run_coordinator, ANALYST_SPECS
    from rca.config import AGENT_BENCHMARK_PATH, current_timestamp_sgt_label

    client_factory = None
    if args.dry_run:
        from rca.stubclient import stub_client_factory
        client_factory = stub_client_factory
        print("[dry-run] Using stub LLM client — no API calls will be made.")

    specialists = None
    if args.quick:
        sales_spec = next(s for s in ANALYST_SPECS if s.name == "sales_analyst")
        specialists = [sales_spec]

    output_dir = None
    if not args.quick:
        from rca.config import PROJECT_ROOT
        label = "dry_run" if args.dry_run else current_timestamp_sgt_label()
        output_dir = PROJECT_ROOT / "data" / "analysis" / "agent_benchmark_runs" / f"{args.store}_{args.dt}_{label}"

    result = run_coordinator(
        store_alias=args.store,
        dt=args.dt,
        specialists=specialists,
        client_factory=client_factory,
        output_dir=output_dir,
    )
    if args.quick:
        print(result.coordinator_report_markdown)
    else:
        print(result.decision_card_markdown)
        if args.full:
            print("\n" + result.coordinator_report_markdown)
    if output_dir:
        print(f"\nArtifacts written to {output_dir}")


def _cmd_bench(args: argparse.Namespace) -> None:
    from rca.bench import run_benchmark
    run_benchmark()


def _cmd_dashboard(args: argparse.Namespace) -> None:
    from rca.report import build_dashboard_html
    from rca.config import PROJECT_ROOT

    output_path = PROJECT_ROOT / "ui" / "public" / "dashboard.html"
    build_dashboard_html(output_path)
    print(f"Dashboard written to {output_path}")


def _cmd_export(args: argparse.Namespace) -> None:
    from rca.evidence import export_evidence_dataset
    from rca.config import PROJECT_ROOT

    output_path = PROJECT_ROOT / "ui" / "public" / "evidence_data.json"
    export_evidence_dataset(output_path)
    print(f"UI data exported to {output_path}")


def _cmd_profile(args: argparse.Namespace) -> None:
    from rca.context import build_context_pack
    from rca.config import CONTEXT_PACK_PATH

    print("Building context pack from data/rca.duckdb...")
    build_context_pack()
    md_path = CONTEXT_PACK_PATH.with_suffix(".md")
    print(f"Written: {CONTEXT_PACK_PATH}")
    print(f"Written: {md_path}")
    print("Review context_pack.md to confirm no tier labels or ID assumptions.")


def _cmd_runs(args: argparse.Namespace) -> None:
    import json
    import sys

    import duckdb

    from rca.config import LOG_DB_PATH

    if not LOG_DB_PATH.exists():
        print("No run log database found. Run a pipeline first.")
        sys.exit(0)

    con = duckdb.connect(str(LOG_DB_PATH), read_only=True)
    rows = con.execute("""
        SELECT
            run_name,
            MIN(timestamp_sgt)  AS started_at,
            MAX(timestamp_sgt)  AS finished_at,
            COUNT(*)            AS events,
            MAX(CASE WHEN action = 'completed' AND actor_name = 'coordinator_pipeline'
                     THEN details_json END) AS completed_json
        FROM run_log_event
        GROUP BY run_name
        ORDER BY MIN(timestamp_sgt) DESC
        LIMIT 30
    """).fetchall()
    con.close()

    if not rows:
        print("Log table exists but is empty.")
        sys.exit(0)

    col_widths = {"run_name": 36, "started_at": 25, "events": 6}
    header = (
        f"{'run':<{col_widths['run_name']}}  "
        f"{'started (SGT)':<{col_widths['started_at']}}  "
        f"{'evts':>{col_widths['events']}}  "
        f"output_dir"
    )
    print(header)
    print("-" * (len(header) + 30))

    for run_name, started_at, _, events, completed_json in rows:
        output_dir = ""
        if completed_json:
            details = json.loads(completed_json)
            output_dir = details.get("output_dir") or ""
        print(
            f"{run_name:<{col_widths['run_name']}}  "
            f"{started_at:<{col_widths['started_at']}}  "
            f"{events:>{col_widths['events']}}  "
            f"{output_dir}"
        )


def _cmd_eval(args: argparse.Namespace) -> None:
    from rca.config import AGENT_BENCHMARK_PATH
    from rca.evaluator import evaluate_benchmark

    client_factory = None
    settings = None
    if args.dry_run:
        from rca.stubclient import stub_client_factory
        from rca.llm import LLMSettings

        client_factory = stub_client_factory
        settings = LLMSettings(
            api_key="dry-run",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        )
        print("[dry-run] Using stub LLM judge.")

    if args.run_dir:
        run_dir = Path(args.run_dir)
    else:
        run_dirs = sorted([path for path in AGENT_BENCHMARK_PATH.iterdir() if path.is_dir()])
        if not run_dirs:
            raise RuntimeError("No benchmark runs found. Run `rca bench` first or pass --run-dir.")
        run_dir = run_dirs[-1]

    payload = evaluate_benchmark(run_dir=run_dir, settings=settings, client_factory=client_factory)
    print(f"Evaluation written to {run_dir / 'eval_report.md'}")
    print(
        f"Scenarios: {payload['scenario_count']}, "
        f"signal matches: {payload['signal_match_count']}, "
        f"unsupported analyst checks: {payload['faithfulness_unsupported_count']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rca",
        description="Retail Insight Agent — root cause analysis for store sales signals",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # rca build
    build_parser = subparsers.add_parser(
        "build",
        help="Ingest parquet into data/rca.duckdb and validate row counts",
    )
    build_parser.set_defaults(func=_cmd_build)

    # rca analyze
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Compute sales signals and export CSVs to data/analysis/",
    )
    analyze_parser.set_defaults(func=_cmd_analyze)

    # rca run
    run_parser = subparsers.add_parser(
        "run",
        help="Run the coordinator pipeline for one store-day",
    )
    run_parser.add_argument("--store", required=True, help="Store alias (e.g. h555)")
    run_parser.add_argument("--dt", required=True, help="Date (YYYY-MM-DD)")
    run_parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode: signal specialist only (no full coordinator)",
    )
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Use stub LLM client — exercises the full pipeline with no API calls",
    )
    run_parser.add_argument(
        "--full",
        action="store_true",
        help="Print the full RCA after the decision card",
    )
    run_parser.set_defaults(func=_cmd_run)

    # rca bench
    bench_parser = subparsers.add_parser(
        "bench",
        help="Run benchmark batch over the 6 fixed scenarios",
    )
    bench_parser.set_defaults(func=_cmd_bench)

    # rca dashboard
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Regenerate ui/public/dashboard.html from analysis CSVs and run logs",
    )
    dashboard_parser.set_defaults(func=_cmd_dashboard)

    # rca export
    export_parser = subparsers.add_parser(
        "export",
        help="Refresh ui/public/evidence_data.json for the Vite evidence viewer",
    )
    export_parser.set_defaults(func=_cmd_export)

    # rca profile
    profile_parser = subparsers.add_parser(
        "profile",
        help="Build data/context_pack.json and context_pack.md from the local DuckDB",
    )
    profile_parser.set_defaults(func=_cmd_profile)

    # rca runs
    runs_parser = subparsers.add_parser(
        "runs",
        help="Print recent run history from data/runs.duckdb",
    )
    runs_parser.set_defaults(func=_cmd_runs)

    # rca eval
    eval_parser = subparsers.add_parser(
        "eval",
        help="Evaluate a benchmark run directory with deterministic checks and an LLM judge",
    )
    eval_parser.add_argument(
        "--run-dir",
        help="Path to a benchmark run directory under data/analysis/agent_benchmark_runs/",
    )
    eval_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Use the stub LLM judge instead of a real API call",
    )
    eval_parser.set_defaults(func=_cmd_eval)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
