from __future__ import annotations

import argparse
import sys

from rca_foundry.multi_agent import run_manager_analyst_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the parallel manager-analyst RCA pipeline.")
    parser.add_argument("--store", required=True, help="Store alias, for example h555")
    parser.add_argument("--dt", required=True, help="Store date, for example 2024-05-16")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    result = run_manager_analyst_pipeline(store_alias=args.store, dt=args.dt)
    print(result.manager_report_markdown)


if __name__ == "__main__":
    main()
