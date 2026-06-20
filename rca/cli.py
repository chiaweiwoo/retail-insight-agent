from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        sanitized = text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
            sys.stdout.encoding or "utf-8",
            errors="replace",
        )
        print(sanitized)


def _cmd_build(args: argparse.Namespace) -> None:
    from rca.database import ingest_to_supabase

    print("Building and pushing all tables to Supabase...")
    counts = ingest_to_supabase()
    for table, count in counts.items():
        print(f"  {table}: {count} rows")
    print("Build complete. All data is now in Supabase.")


def _cmd_analyze(args: argparse.Namespace) -> None:
    from rca.config import make_supabase_client, DEFAULT_DROP_THRESHOLD_PCT, DEFAULT_LIFT_THRESHOLD_PCT, BUSINESS_TARGET_GROWTH_FACTOR
    from rca.signals import build_signal_series
    from rca.database import push_city_signal
    import pandas as pd

    client = make_supabase_client()

    print("Loading actuals from rca_city_series...")
    resp = client.table("rca_city_series").select(
        "city_id,dt,total_sales,weekday,density_tier,holiday_name_inferred"
    ).limit(2000).execute()
    actuals = pd.DataFrame(resp.data or [])
    if actuals.empty:
        print("rca_city_series is empty — run 'rca build' first.")
        return

    print("Loading finance forecast from rca_finance_forecast...")
    resp = client.table("rca_finance_forecast").select("city_id,dt,forecast_sales").execute()
    forecast = pd.DataFrame(resp.data or [])
    if forecast.empty:
        print("rca_finance_forecast is empty — run 'rca build' first.")
        return

    print(f"Computing signal series (business target = forecast × {BUSINESS_TARGET_GROWTH_FACTOR})...")
    signals = build_signal_series(actuals, forecast)

    # Distribution summary
    eligible = signals[signals["business_target"].notna()]
    total = len(eligible)
    drop_count = int((eligible["signal_label"] == "drop").sum())
    lift_count = int((eligible["signal_label"] == "lift").sum())
    triggered = drop_count + lift_count
    trigger_rate = triggered / total * 100 if total else 0.0

    print()
    print(f"  Eligible city-days (with forecast): {total}")
    print(f"  Drop  (≤ {DEFAULT_DROP_THRESHOLD_PCT:+.0f}%): {drop_count:>4}  ({drop_count / total * 100:.1f}%)")
    print(f"  Lift  (≥ +{DEFAULT_LIFT_THRESHOLD_PCT:.0f}%):   {lift_count:>4}  ({lift_count / total * 100:.1f}%)")
    print(f"  Triggered total:            {triggered:>4}  ({trigger_rate:.1f}%)")

    pct = eligible["target_deviation_pct"].dropna()
    print()
    print(f"  target_deviation_pct — p10: {pct.quantile(0.10):+.1f}%  median: {pct.quantile(0.50):+.1f}%  p90: {pct.quantile(0.90):+.1f}%")
    print()

    print("Pushing to Supabase rca_city_signal...")
    pushed = push_city_signal(signals, client)
    print(f"  {pushed} rows upserted.")
    print("Done.")


def _run_single_day(
    city_id: int,
    dt: str,
    *,
    quick: bool,
    dry_run: bool,
    full: bool,
    reflect: bool,
    client_factory,
) -> None:
    from rca.graph import run_rca_graph
    from rca.agents import ANALYST_SPECS
    from rca.config import current_timestamp_sgt_label, PROJECT_ROOT

    specialists = None
    if quick:
        sales_spec = next(s for s in ANALYST_SPECS if s.name == "sales_analyst")
        specialists = [sales_spec]

    output_dir = None
    if not quick:
        label = "dry_run" if dry_run else current_timestamp_sgt_label()
        output_dir = PROJECT_ROOT / "data" / "analysis" / "agent_benchmark_runs" / f"city{city_id}_{dt}_{label}"

    result = run_rca_graph(
        city_id=city_id,
        dt=dt,
        specialists=specialists,
        client_factory=client_factory,
        output_dir=output_dir,
        enable_reflection=reflect,
    )
    if quick:
        _safe_print(result.coordinator_report_markdown)
    else:
        _safe_print(result.decision_card_markdown)
        if full:
            _safe_print("\n" + result.coordinator_report_markdown)
    if output_dir:
        print(f"\nArtifacts written to {output_dir}")


def _cmd_run(args: argparse.Namespace) -> None:
    client_factory = None
    if args.dry_run:
        from rca.stubclient import stub_client_factory
        client_factory = stub_client_factory
        print("[dry-run] Using stub LLM client — no API calls will be made.")

    if args.dt:
        # Single-day mode
        _run_single_day(
            args.city, args.dt,
            quick=args.quick, dry_run=args.dry_run, full=args.full,
            reflect=getattr(args, "reflect", False), client_factory=client_factory,
        )
    else:
        # Trigger-scan mode: run all triggered dates oldest→latest
        from rca.signals import get_trigger_dates_for_city
        dates = get_trigger_dates_for_city(args.city)
        if not dates:
            print(f"No triggered dates found for city {args.city}. Run 'rca analyze' first.")
            return
        print(f"City {args.city}: {len(dates)} triggered date(s). Running oldest→latest...")
        for i, dt in enumerate(dates, 1):
            print(f"\n[{i}/{len(dates)}] city {args.city} — {dt}")
            _run_single_day(
                args.city, dt,
                quick=args.quick, dry_run=args.dry_run, full=args.full,
                reflect=getattr(args, "reflect", False), client_factory=client_factory,
            )


def _cmd_bench(args: argparse.Namespace) -> None:
    from rca.bench import run_benchmark
    client_factory = None
    if getattr(args, "dry_run", False):
        from rca.stubclient import stub_client_factory
        client_factory = stub_client_factory
        print("[dry-run] Using stub LLM client for benchmark.")
    run_benchmark(client_factory=client_factory)


def _cmd_profile(args: argparse.Namespace) -> None:
    from rca.context import build_context_pack
    from rca.config import CONTEXT_PACK_PATH

    print("Building context pack from Supabase rca_city_series...")
    build_context_pack()
    md_path = CONTEXT_PACK_PATH.with_suffix(".md")
    print(f"Written: {CONTEXT_PACK_PATH}")
    print(f"Written: {md_path}")
    print("Review context_pack.md to confirm no tier labels or ID assumptions.")


def _cmd_runs(args: argparse.Namespace) -> None:
    import os
    import sys

    from rca.config import make_supabase_client

    if not os.getenv("SUPABASE_URL"):
        print("SUPABASE_URL not set — no run history available.")
        sys.exit(0)

    client = make_supabase_client()
    result = (
        client
        .table("rca_outcome")
        .select("run_name,city_id,dt,signal_label,confidence,escalated,brief_headline,generated_at")
        .order("generated_at", desc=True)
        .limit(30)
        .execute()
    )
    rows = result.data or []

    if not rows:
        print("No runs recorded yet.")
        sys.exit(0)

    col = {"run_name": 40, "city_id": 7, "dt": 12, "conf": 8}
    header = (
        f"{'run':<{col['run_name']}}  "
        f"{'city':<{col['city_id']}}  "
        f"{'dt':<{col['dt']}}  "
        f"{'conf':<{col['conf']}}  "
        f"headline"
    )
    print(header)
    print("-" * (len(header) + 20))

    for row in rows:
        escalated = " [ESC]" if row.get("escalated") else ""
        print(
            f"{str(row.get('run_name','')):<{col['run_name']}}  "
            f"{str(row.get('city_id','')):<{col['city_id']}}  "
            f"{str(row.get('dt','')):<{col['dt']}}  "
            f"{str(row.get('confidence','')):<{col['conf']}}  "
            f"{row.get('brief_headline','')}{escalated}"
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
        # Sort by mtime descending — most recent run first.
        # Bench runs contain scenario subdirs; single runs have coordinator_trace.json at root.
        all_dirs = [p for p in AGENT_BENCHMARK_PATH.iterdir() if p.is_dir()]
        if not all_dirs:
            raise RuntimeError("No benchmark runs found. Run 'rca bench' first or pass --run-dir.")
        # Prefer a bench run dir (has subdirectories with traces) over a single-run dir
        bench_dirs = [
            p for p in all_dirs
            if any((p / child.name / "coordinator_trace.json").exists() for child in p.iterdir() if child.is_dir())
        ]
        candidates = bench_dirs if bench_dirs else all_dirs
        run_dir = max(candidates, key=lambda p: p.stat().st_mtime)

    payload = evaluate_benchmark(run_dir=run_dir, settings=settings, client_factory=client_factory)
    print(f"Evaluation written to {run_dir / 'eval_report.md'}")
    print(
        f"Scenarios: {payload['scenario_count']}, "
        f"signal matches: {payload['signal_match_count']}, "
        f"unsupported analyst checks: {payload['faithfulness_unsupported_count']}"
    )


def _cmd_story(args: argparse.Namespace) -> None:
    from rca.report import build_story_report

    client_factory = None
    settings = None
    use_llm = not args.no_llm
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
        use_llm = True
        print("[dry-run] Using stub LLM story writer.")

    run_dir = Path(args.run_dir)
    city_id, dt = build_story_report(
        run_dir=run_dir,
        use_llm=use_llm,
        settings=settings,
        client_factory=client_factory,
    )
    if args.dry_run:
        print(f"[dry-run] Story narrative generated for city {city_id} on {dt} (not written to Supabase).")
    else:
        print(f"Story narrative upserted to Supabase rca_outcome for city {city_id} on {dt}.")


def _cmd_mcp(args: argparse.Namespace) -> None:
    from rca.mcp_server import mcp
    mcp.run()


def _cmd_distil(args: argparse.Namespace) -> None:
    import os
    from rca.llm import load_llm_settings, LLMSettings
    from rca.profiles import distil_city_profile, distil_all_cities

    dry_run = getattr(args, "dry_run", False)
    client_factory = None
    settings = None

    if dry_run:
        from rca.stubclient import stub_client_factory
        client_factory = stub_client_factory
        settings = LLMSettings(
            api_key="dry-run",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        )
        print("[dry-run] Using stub LLM — profile will not be written to Supabase.")
    else:
        if not os.getenv("SUPABASE_URL"):
            print("SUPABASE_URL not set — cannot write profiles.")
            return
        settings = load_llm_settings()

    if args.city is not None:
        profile = distil_city_profile(
            args.city, settings=settings, client_factory=client_factory, dry_run=dry_run
        )
        print(f"Profile for city {args.city}:")
        print(profile)
        if not dry_run:
            print(f"\nWritten to Supabase rca_city_profile.")
    else:
        results = distil_all_cities(settings=settings, client_factory=client_factory, dry_run=dry_run)
        if not results:
            print("No cities with prior outcomes found.")
            return
        for city_id, profile in results:
            print(f"\n--- city {city_id} ---")
            print(profile)
        if not dry_run:
            print(f"\nWritten {len(results)} profiles to Supabase rca_city_profile.")


def _cmd_reset_memory(args: argparse.Namespace) -> None:
    import os
    from rca.profiles import reset_city_profile

    if not os.getenv("SUPABASE_URL"):
        print("SUPABASE_URL not set — nothing to reset.")
        return

    if args.city is not None:
        count = reset_city_profile(args.city)
        print(f"Deleted profile for city {args.city} ({count} row(s) removed).")
    elif args.all:
        count = reset_city_profile(city_id=None)
        print(f"Deleted all city profiles ({count} row(s) removed).")
    else:
        print("Specify --city ID or --all.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rca",
        description="Retail Insight Agent — root cause analysis for city-aggregate sales signals",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # rca build
    build_parser = subparsers.add_parser(
        "build",
        help="Ingest parquet and push all tables directly to Supabase",
    )
    build_parser.set_defaults(func=_cmd_build)

    # rca analyze
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Compute business-target deviations, label triggers, push to rca_city_signal",
    )
    analyze_parser.set_defaults(func=_cmd_analyze)

    # rca run
    run_parser = subparsers.add_parser(
        "run",
        help="Run the coordinator pipeline for one city-day",
    )
    run_parser.add_argument("--city", required=True, type=int, help="City ID (integer 0–17)")
    run_parser.add_argument(
        "--dt",
        default=None,
        help="Date (YYYY-MM-DD). Omit to run all triggered dates for the city oldest→latest.",
    )
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
    run_parser.add_argument(
        "--reflect",
        action="store_true",
        help="Run a bounded self-audit reflection after the SLT brief",
    )
    run_parser.set_defaults(func=_cmd_run)

    # rca bench
    bench_parser = subparsers.add_parser(
        "bench",
        help="Run benchmark batch over the 6 fixed scenarios",
    )
    bench_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Use stub LLM client — no API calls",
    )
    bench_parser.set_defaults(func=_cmd_bench)

    # rca profile
    profile_parser = subparsers.add_parser(
        "profile",
        help="Build data/context_pack.json and context_pack.md from Supabase",
    )
    profile_parser.set_defaults(func=_cmd_profile)

    # rca distil
    distil_parser = subparsers.add_parser(
        "distil",
        help="Generate episodic city memory profiles from prior RCA outcomes",
    )
    distil_parser.add_argument(
        "--city",
        type=int,
        default=None,
        help="City ID to distil (omit to distil all cities with history)",
    )
    distil_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Generate profile without writing to Supabase",
    )
    distil_parser.set_defaults(func=_cmd_distil)

    # rca reset-memory
    reset_mem_parser = subparsers.add_parser(
        "reset-memory",
        help="Delete stored episodic profiles from Supabase rca_city_profile",
    )
    reset_mem_parser.add_argument("--city", type=int, default=None, help="City ID to reset")
    reset_mem_parser.add_argument(
        "--all", action="store_true", help="Reset profiles for all cities"
    )
    reset_mem_parser.set_defaults(func=_cmd_reset_memory)

    # rca runs
    runs_parser = subparsers.add_parser(
        "runs",
        help="Print recent run history from Supabase rca_outcome",
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

    # rca story
    story_parser = subparsers.add_parser(
        "story",
        help="Generate a story narrative from a run folder and upsert to Supabase",
    )
    story_parser.add_argument(
        "--run-dir",
        required=True,
        help="Path to a run folder containing run_trace.json or coordinator_trace.json",
    )
    story_parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip the LLM polish and use deterministic assembly only",
    )
    story_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Generate narrative without writing to Supabase",
    )
    story_parser.set_defaults(func=_cmd_story)

    # rca mcp
    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Launch MCP tool server (read-only)",
    )
    mcp_parser.set_defaults(func=_cmd_mcp)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
