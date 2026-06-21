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
    from rca.stubclient import stub_client_factory

    client_factory = stub_client_factory if args.dry_run else None
    result = run_rca_graph(city_id=args.city, dt=args.date, client_factory=client_factory)
    _safe_print(result["final_report"])


def _cmd_mcp(_: argparse.Namespace) -> None:
    from rca.mcp_server import mcp

    mcp.run()


def _cmd_replay(args: argparse.Namespace) -> None:
    from rca.replay import replay_city

    if not args.no_reset:
        _safe_print(
            f"WARNING: --reset is ON. This will delete all outcomes, events, completions,\n"
            f"         memory, evidence_cache, and external_events for city {args.city}.\n"
            f"         Pass --no-reset to skip. Proceeding in 0s...\n"
        )

    replay_city(
        args.city,
        reset=not args.no_reset,
        dry_run=args.dry_run,
        limit=args.limit,
        review=not args.no_review,
        batch_id=args.batch_id,
    )


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
    run_parser.add_argument("--date", "--dt", required=True, dest="date", help="Date in YYYY-MM-DD format")
    run_parser.add_argument("--dry-run", action="store_true", dest="dry_run", help="Use the stub LLM client")
    run_parser.set_defaults(func=_cmd_run)

    mcp_parser = subparsers.add_parser(
        "mcp",
        help="Launch the FastMCP tool server",
    )
    mcp_parser.set_defaults(func=_cmd_mcp)

    replay_parser = subparsers.add_parser(
        "replay",
        help="Reset state and rerun all triggered signal dates for a city, with quality review",
    )
    replay_parser.add_argument("--city", required=True, type=int, help="City ID (0-17)")
    replay_parser.add_argument(
        "--no-reset",
        action="store_true",
        dest="no_reset",
        help="Skip the destructive state reset (keep existing memory and outputs)",
    )
    replay_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Use the stub LLM client for both RCA and the alignment reviewer",
    )
    replay_parser.add_argument(
        "--limit",
        type=int,
        default=None,
        dest="limit",
        metavar="N",
        help="Only process the first N triggered signal dates",
    )
    replay_parser.add_argument(
        "--no-review",
        action="store_true",
        dest="no_review",
        help="Skip the LLM alignment review and replay_review storage",
    )
    replay_parser.add_argument(
        "--batch-id",
        default=None,
        dest="batch_id",
        help="Override the batch ID (default: timestamp)",
    )
    replay_parser.set_defaults(func=_cmd_replay)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
