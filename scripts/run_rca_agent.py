from __future__ import annotations

import argparse
import sys

from rca_foundry.agent import run_rca_agent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the retail RCA tool-calling agent.")
    parser.add_argument("--store", required=True, help="Store alias, for example h555")
    parser.add_argument("--dt", required=True, help="Store date, for example 2024-05-16")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    result = run_rca_agent(store_alias=args.store, dt=args.dt)
    print(result.report_markdown)


if __name__ == "__main__":
    main()
