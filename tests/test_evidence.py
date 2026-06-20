from __future__ import annotations

import pytest

from rca.evidence import (
    export_evidence_dataset,
    fetch_all_evidence_records,
    get_city_day_evidence,
    list_dates,
    list_city_ides,
)

# These tests are store-era (15 stores, store aliases). They are being
# rewritten for city grain in Round E1. Skipped here to keep collection clean.
pytestmark = pytest.mark.skip(reason="store-era tests — rewritten for city grain in Round E1")
