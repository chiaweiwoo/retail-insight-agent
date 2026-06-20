"""Smoke tests for the Supabase-backed data layer.

These tests require SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to be set.
If the env vars are absent (CI without secrets), all tests skip gracefully.
"""
from __future__ import annotations

import os

import pytest

from rca.config import CITY_IDS, DATE_START, DATE_END


pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL"),
    reason="SUPABASE_URL not set — skipping Supabase smoke tests",
)


def test_rca_city_series_has_rows() -> None:
    from rca.config import make_supabase_client
    client = make_supabase_client()
    resp = client.table("rca_city_series").select("city_id").limit(1).execute()
    assert resp.data, "rca_city_series is empty — run 'rca build' first"


def test_rca_city_signal_v_returns_rows() -> None:
    from rca.config import make_supabase_client
    client = make_supabase_client()
    resp = (
        client.table("rca_city_signal_v")
        .select("city_id,dt,signal_label")
        .limit(5)
        .execute()
    )
    assert resp.data, "rca_city_signal_v is empty — check migration 0009"
    for row in resp.data:
        assert row["signal_label"] in {"drop", "lift", "neutral", "insufficient_history"}


def test_evidence_fetcher_returns_expected_shape() -> None:
    from rca.evidence import get_city_day_evidence
    evidence = get_city_day_evidence(city_id=0, dt=DATE_START)
    assert "sales" in evidence
    assert "stockout" in evidence
    assert "discount" in evidence
    assert "activity" in evidence
    assert "holiday" in evidence
    assert "weather" in evidence
    assert len(evidence["sales"]["hourly_sales"]) == 24


def test_signal_frame_loads_all_cities() -> None:
    from rca.tools import _signal_frame
    frame = _signal_frame()
    loaded_cities = set(frame["city_id"].unique())
    expected = set(CITY_IDS)
    assert expected.issubset(loaded_cities), (
        f"Missing cities in signal frame: {expected - loaded_cities}"
    )
