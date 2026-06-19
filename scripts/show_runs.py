"""Print a summary table of recent pipeline runs from run_logs.duckdb."""

from __future__ import annotations

import json
import sys

import duckdb

from rca_foundry.config import LOG_DB_PATH


def main() -> None:
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
            MAX(CASE WHEN action = 'completed' AND actor_name = 'manager_pipeline'
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

    col_widths = {"run_name": 36, "started_at": 25, "events": 6, "output_dir": 60}
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


if __name__ == "__main__":
    main()
