from __future__ import annotations

import pytest

from rca.tools import (
    execute_tool,
    get_activity_context,
    get_calendar_weather_context,
    get_discount_context,
    get_prior_rca,
    get_peer_city_context,
    get_sales_context,
    get_signal_evidence,
    get_stockout_context,
    get_tool_schemas,
)

# These tests are store-era (store aliases, store-grain assertions). They are
# being rewritten for city grain in Round E1. Skipped here to keep collection clean.
pytestmark = pytest.mark.skip(reason="store-era tests — rewritten for city grain in Round E1")
