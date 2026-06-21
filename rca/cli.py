from __future__ import annotations

import argparse
import sys


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write((text + "\n").encode("utf-8", errors="replace"))
        sys.stdout.flush()


def _cmd_build(_: argparse.Namespace) -> None:
    from rca.database import ingest_to_supabase

    print("Rebuilding RCA base tables from parquet...")
    counts = ingest_to_supabase()
    for table, count in counts.items():
        print(f"  {table}: {count} rows")
    print("Build complete.")


def _cmd_signal(_: argparse.Namespace) -> None:
    from rca.database import materialize_signals_to_supabase

    print("Materializing signal table from ingested RCA tables...")
    counts = materialize_signals_to_supabase()
    for table, count in counts.items():
        print(f"  {table}: {count} rows")
    print("Signal build complete.")


def _cmd_run(args: argparse.Namespace) -> None:
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=args.city, dt=args.date)
    _safe_print(result["final_report"])


def _cmd_mcp(_: argparse.Namespace) -> None:
    from rca.mcp_server import mcp

    mcp.run()


def _cmd_export(_args: argparse.Namespace) -> None:
    _safe_print("rca export is disabled. Confirm with the team before re-enabling.")


def _cmd_simulate(_args: argparse.Namespace) -> None:
    _safe_print("rca simulate is disabled. Confirm with the team before re-enabling.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rca",
        description="Retail Insight Agent v2 - city/date autonomous RCA learning harness",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build",
        help="Reset and repopulate base RCA tables from parquet",
    )
    build_parser.set_defaults(func=_cmd_build)

    signal_parser = subparsers.add_parser(
        "signal",
        help="Rebuild the RCA signal table from ingested city/date tables",
    )
    signal_parser.set_defaults(func=_cmd_signal)

    run_parser = subparsers.add_parser(
        "run",
        help="Run the LangGraph RCA workflow for one city/date",
    )
    run_parser.add_argument("--city", required=True, type=int, help="City ID (0-17)")
    run_parser.add_argument("--date", required=True, dest="date", help="Date in YYYY-MM-DD format")
    run_parser.set_defaults(func=_cmd_run)

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Launch the FastMCP tool server",
    )
    mcp_parser.set_defaults(func=_cmd_mcp)

    export_parser = subparsers.add_parser(
        "export",
        help="Export simulate_review rows for a city to a local JSON file",
    )
    export_parser.add_argument("--city", required=True, type=int, help="City ID (0-17)")
    export_parser.add_argument("--batch", default=None, help="Filter to a specific batch_id")
    export_parser.add_argument("--output", required=True, help="Output file path (e.g. results/city0_flash.json)")
    export_parser.set_defaults(func=_cmd_export)

    simulate_parser = subparsers.add_parser(
        "simulate",
        help="Run a cold-start city simulation across all triggered signal dates",
    )
    simulate_parser.add_argument("--city", required=True, type=int, help="City ID (0-17)")
    simulate_parser.set_defaults(func=_cmd_simulate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
