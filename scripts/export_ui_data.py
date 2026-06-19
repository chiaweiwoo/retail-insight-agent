from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from rca_foundry.query import export_evidence_dataset


def main() -> None:
    output_path = PROJECT_ROOT / "ui" / "public" / "evidence_data.json"
    export_evidence_dataset(output_path)
    print(f"UI data exported: {output_path}")


if __name__ == "__main__":
    main()
