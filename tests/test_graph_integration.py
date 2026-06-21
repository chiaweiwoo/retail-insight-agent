"""End-to-end integration test for run_rca_graph with the stub client.

Patches only the DB seam so the full graph (investigation_loop → decision →
evaluation → memory → record) exercises real Python code without hitting
Supabase or a real LLM.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rca.stubclient import stub_client_factory

_SIGNAL = {
    "city_id": 0,
    "dt": "2024-04-01",
    "signal_label": "drop",
    "total_sales": 850.0,
    "expected_sales": 1000.0,
    "deviation_pct": -15.0,
    "abs_deviation_pct": 15.0,
    "goal_method": "weekday_baseline",
    "signal_strength": "strong",
    "baseline_quality": "good",
    "signal_reason": "Drop exceeds threshold.",
    "priority_score": 2.5,
    "weekday": "Monday",
    "holiday_name_inferred": "",
    "first_hypothesis_hints": {},
    "build_version": "stub",
    "generated_at": "2024-04-01T00:00:00+08:00",
}

_FAKE_EXECUTE_RESULT = MagicMock(data=[], count=0)


def _fake_client():
    """Minimal Supabase-like client that returns empty results for all operations."""
    client = MagicMock()
    client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = _FAKE_EXECUTE_RESULT
    client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = _FAKE_EXECUTE_RESULT
    client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = _FAKE_EXECUTE_RESULT
    client.table.return_value.select.return_value.limit.return_value.execute.return_value = _FAKE_EXECUTE_RESULT
    client.table.return_value.upsert.return_value.execute.return_value = _FAKE_EXECUTE_RESULT
    client.table.return_value.insert.return_value.execute.return_value = _FAKE_EXECUTE_RESULT
    return client


@pytest.fixture(autouse=True)
def _patch_supabase(monkeypatch):
    """Replace make_supabase_schema_client everywhere it is imported."""
    fake = _fake_client()
    monkeypatch.setattr("rca.config.make_supabase_schema_client", lambda schema=None: fake)
    monkeypatch.setattr("rca.memory.make_supabase_schema_client", lambda schema=None: fake)
    monkeypatch.setattr("rca.outcomes.make_supabase_schema_client", lambda schema=None: fake)
    monkeypatch.setattr("rca.runlog.make_supabase_schema_client", lambda schema=None: fake)
    monkeypatch.setattr("rca.database.make_supabase_schema_client", lambda schema=None: fake)


@pytest.fixture(autouse=True)
def _patch_signal(monkeypatch):
    """Return a canned signal row without DB."""
    monkeypatch.setattr("rca.graph.get_signal_row", lambda city_id, dt: _SIGNAL)
    monkeypatch.setattr("rca.graph.get_memory_notes", lambda city_id, limit=5: [])


def test_run_rca_graph_stub_completes_without_error():
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=0, dt="2024-04-01", client_factory=stub_client_factory)

    assert isinstance(result, dict)


def test_run_rca_graph_stub_returns_final_report():
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=0, dt="2024-04-01", client_factory=stub_client_factory)

    final_report = result.get("final_report", "")
    assert isinstance(final_report, str)
    assert len(final_report) > 0


def test_run_rca_graph_stub_report_contains_coordinator_headline():
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=0, dt="2024-04-01", client_factory=stub_client_factory)

    # The coordinator stub contains this phrase — confirms the coordinator node ran
    assert "under plan" in result["final_report"].lower() or "sales" in result["final_report"].lower()


def test_run_rca_graph_stub_has_evidence_ledger():
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=0, dt="2024-04-01", client_factory=stub_client_factory)

    assert "evidence_ledger" in result
    assert isinstance(result["evidence_ledger"], list)


def test_run_rca_graph_stub_has_evaluation_score():
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=0, dt="2024-04-01", client_factory=stub_client_factory)

    evaluation = result.get("evaluation", {})
    assert isinstance(evaluation, dict)
    assert "score" in evaluation
    score = evaluation["score"]
    assert isinstance(score, (int, float))
    assert 0.0 <= score <= 1.0


def test_run_rca_graph_stub_has_decision_brief():
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=0, dt="2024-04-01", client_factory=stub_client_factory)

    brief = result.get("decision_brief", {})
    assert isinstance(brief, dict)
    assert "headline" in brief
    assert "confidence" in brief


def test_run_rca_graph_stub_round_count_positive():
    from rca.graph import run_rca_graph

    result = run_rca_graph(city_id=0, dt="2024-04-01", client_factory=stub_client_factory)

    assert result.get("round_count", 0) >= 1
