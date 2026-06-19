from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from rca_foundry.config import DB_PATH
from rca_foundry.ingestion import ingest_to_duckdb


def main() -> None:
    row_counts = ingest_to_duckdb()
    print(f"Ingestion complete: {DB_PATH}")
    for table_name, row_count in row_counts.items():
        print(f"{table_name}: {row_count}")


if __name__ == "__main__":
    main()
