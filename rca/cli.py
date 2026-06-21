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


def _cmd_export(args: argparse.Namespace) -> None:
    import json
    import pathlib
    from rca.config import (
        TABLE_COMPLETIONS, TABLE_EVENTS, TABLE_EVIDENCE_CACHE,
        TABLE_EXTERNAL_EVENTS, TABLE_MEMORY, TABLE_OUTCOMES,
        TABLE_SIMULATE_REVIEW, make_supabase_schema_client,
    )

    client = make_supabase_schema_client()
    bundle: dict = {"city_id": args.city, "tables": {}}

    # Tables reset-and-repopulated per simulate run — export current state for city
    plain_tables = [
        TABLE_OUTCOMES, TABLE_EVENTS, TABLE_COMPLETIONS,
        TABLE_MEMORY, TABLE_EVIDENCE_CACHE, TABLE_EXTERNAL_EVENTS,
    ]
    for table in plain_tables:
        rows = (client.table(table).select("*").eq("city_id", args.city).order("id").execute().data or [])
        bundle["tables"][table] = rows
        _safe_print(f"  {table}: {len(rows)} rows")

    # simulate_review keeps all batches — filter by batch_id if given
    q = client.table(TABLE_SIMULATE_REVIEW).select("*").eq("city_id", args.city).order("created_at")
    if args.batch:
        q = q.eq("batch_id", args.batch)
    rows = q.execute().data or []
    bundle["tables"][TABLE_SIMULATE_REVIEW] = rows
    _safe_print(f"  {TABLE_SIMULATE_REVIEW}: {len(rows)} rows" + (f" (batch {args.batch})" if args.batch else ""))

    out = pathlib.Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    _safe_print(f"Exported to {out}")


def _cmd_simulate(args: argparse.Namespace) -> None:
    import json
    import pathlib
    from rca.simulate import simulate_city
    from rca.config import (
        TABLE_COMPLETIONS, TABLE_EVENTS, TABLE_EVIDENCE_CACHE,
        TABLE_EXTERNAL_EVENTS, TABLE_MEMORY, TABLE_OUTCOMES,
        TABLE_SIMULATE_REVIEW, make_supabase_schema_client,
    )

    _safe_print(
        f"Starting cold-start city simulation for city {args.city}.\n"
        f"This will delete existing outcomes, events, completions,\n"
        f"memory, evidence_cache, and external_events for that city first.\n"
    )

    summary = simulate_city(args.city)

    # Auto-export full city bundle immediately after simulation completes
    client = make_supabase_schema_client()
    bundle: dict = {"city_id": args.city, "batch_id": summary.batch_id, "tables": {}}
    plain_tables = [
        TABLE_OUTCOMES, TABLE_EVENTS, TABLE_COMPLETIONS,
        TABLE_MEMORY, TABLE_EVIDENCE_CACHE, TABLE_EXTERNAL_EVENTS,
    ]
    for table in plain_tables:
        rows = (client.table(table).select("*").eq("city_id", args.city).order("id").execute().data or [])
        bundle["tables"][table] = rows
    rows = (
        client.table(TABLE_SIMULATE_REVIEW).select("*")
        .eq("city_id", args.city).eq("batch_id", summary.batch_id)
        .order("created_at").execute().data or []
    )
    bundle["tables"][TABLE_SIMULATE_REVIEW] = rows

    out = pathlib.Path(f"results/city{args.city}_{summary.batch_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    _safe_print(f"\nAuto-exported {sum(len(v) for v in bundle['tables'].values())} total rows to {out}")


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
