from __future__ import annotations

import argparse


def _cmd_build(_: argparse.Namespace) -> None:
    from rca.database import ingest_to_supabase

    print("Rebuilding RCA tables from parquet...")
    counts = ingest_to_supabase()
    for table, count in counts.items():
        print(f"  {table}: {count} rows")
    print("Build complete.")


def _cmd_run(args: argparse.Namespace) -> None:
    from rca.graph import run_rca_graph
    from rca.stubclient import stub_client_factory

    client_factory = stub_client_factory if args.dry_run else None
    result = run_rca_graph(city_id=args.city, dt=args.date, client_factory=client_factory)
    print(result["final_report"])


def _cmd_mcp(_: argparse.Namespace) -> None:
    from rca.mcp_server import mcp

    mcp.run()


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="rca",
        description="Retail Insight Agent v2 - city/date autonomous RCA learning harness",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build",
        help="Reset and repopulate RCA schema tables from parquet",
    )
    build_parser.set_defaults(func=_cmd_build)

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

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
