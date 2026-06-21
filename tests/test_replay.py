"""Tests for the city simulation harness."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rca.replay import ReplaySummary, find_signal_dates, reset_city_state


@pytest.fixture()
def fake_client():
    client = MagicMock()
    client.table.return_value.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}, {}])
    client.table.return_value.select.return_value.eq.return_value.in_.return_value.order.return_value.execute.return_value = MagicMock(
        data=[{"dt": "2024-04-01"}, {"dt": "2024-04-03"}, {"dt": "2024-04-11"}]
    )
    return client


@pytest.fixture(autouse=True)
def _patch_supabase(monkeypatch, fake_client):
    monkeypatch.setattr("rca.replay.make_supabase_schema_client", lambda schema=None: fake_client)
    monkeypatch.setattr("rca.config.make_supabase_schema_client", lambda schema=None: fake_client)


def test_reset_city_state_returns_dict(fake_client):
    result = reset_city_state(city_id=0)
    assert isinstance(result, dict)


def test_reset_city_state_covers_all_tables(fake_client):
    result = reset_city_state(city_id=0)
    expected_tables = {"outcomes", "events", "completions", "memory", "evidence_cache", "external_events"}
    assert set(result.keys()) == expected_tables


def test_reset_city_state_calls_delete(fake_client):
    reset_city_state(city_id=5)
    assert fake_client.table.call_count >= 6


def test_find_signal_dates_returns_list(fake_client):
    with patch("rca.replay.make_supabase_schema_client", return_value=fake_client):
        dates = find_signal_dates(city_id=0)
    assert isinstance(dates, list)


def test_find_signal_dates_all_strings(fake_client):
    with patch("rca.replay.make_supabase_schema_client", return_value=fake_client):
        dates = find_signal_dates(city_id=0)
    assert all(isinstance(d, str) for d in dates)


def test_simulate_city_always_resets_and_reviews_outputs(monkeypatch):
    """simulate_city always cold-starts and always reviews outputs."""
    from rca.replay import simulate_city
    from rca.stubclient import stub_client_factory

    monkeypatch.setattr("rca.replay.find_signal_dates", lambda city_id: ["2024-04-01"])
    reset_calls = []
    monkeypatch.setattr("rca.replay.reset_city_state", lambda city_id: reset_calls.append(city_id) or {})

    fake_result = {
        "run_id": "city_0_2024-04-01_stub",
        "final_report": "# Decision Card\n- headline: Stub headline",
        "decision_brief": {
            "headline": "Stub",
            "confidence": "low",
            "monitoring_plan": {"metrics_to_watch": ["stockout_product_rate"]},
            "unknowns": ["Margin unavailable."],
        },
        "evidence_ledger": [{"id": "ev_001", "evidence_type": "inference", "summary": "stub"}],
        "evaluation": {"score": 0.9, "passed": True},
        "signal_evidence": {"signal_label": "drop"},
        "round_count": 1,
        "investigation_rounds": [],
        "memory_note": "",
    }
    monkeypatch.setattr("rca.replay.run_rca_graph", lambda city_id, dt, settings=None, client_factory=None: fake_result)

    stored_reviews = []
    monkeypatch.setattr("rca.replay.store_replay_review", lambda **kwargs: stored_reviews.append(kwargs))

    summary = simulate_city(0, client_factory=stub_client_factory)

    assert isinstance(summary, ReplaySummary)
    assert summary.total_dates == 1
    assert summary.passed_count == 1
    assert summary.avg_eval_score == pytest.approx(0.9)
    assert summary.avg_alignment_score is not None
    assert len(stored_reviews) == 1
    assert reset_calls == [0]


def test_replay_city_wrapper_forces_reset(monkeypatch):
    """The legacy wrapper still forces a cold-start simulation."""
    from rca.replay import replay_city
    from rca.stubclient import stub_client_factory

    monkeypatch.setattr("rca.replay.find_signal_dates", lambda city_id: ["2024-04-01"])
    reset_calls = []
    monkeypatch.setattr("rca.replay.reset_city_state", lambda city_id: reset_calls.append(city_id) or {})

    fake_result = {
        "run_id": "city_0_2024-04-01_stub",
        "final_report": "# Decision Card",
        "decision_brief": {
            "headline": "Stub headline",
            "confidence": "low",
            "monitoring_plan": {"metrics_to_watch": ["stockout_product_rate"]},
            "unknowns": ["Margin unavailable."],
        },
        "evidence_ledger": [{"id": "ev_001", "evidence_type": "inference", "summary": "stub"}],
        "evaluation": {"score": 1.0, "passed": True},
        "signal_evidence": {"signal_label": "drop"},
        "round_count": 1,
        "investigation_rounds": [],
        "memory_note": "",
    }
    monkeypatch.setattr("rca.replay.run_rca_graph", lambda city_id, dt, settings=None, client_factory=None: fake_result)
    monkeypatch.setattr("rca.replay.store_replay_review", lambda **kwargs: None)

    summary = replay_city(0, reset=False, client_factory=stub_client_factory)

    assert summary.total_dates == 1
    assert summary.avg_alignment_score is not None
    assert reset_calls == [0]


def test_simulate_city_returns_correct_top_cons(monkeypatch):
    """Top cons are aggregated across dates and sorted by frequency."""
    from rca.replay import simulate_city
    from rca.reviewer import ReplayReview

    monkeypatch.setattr("rca.replay.find_signal_dates", lambda city_id: ["2024-04-01", "2024-04-03"])
    monkeypatch.setattr("rca.replay.reset_city_state", lambda city_id: {})

    fake_result = {
        "run_id": "stub",
        "final_report": "",
        "decision_brief": {},
        "evidence_ledger": [],
        "evaluation": {"score": 0.8, "passed": True},
        "signal_evidence": {"signal_label": "drop"},
        "round_count": 1,
        "investigation_rounds": [],
        "memory_note": "",
    }
    monkeypatch.setattr("rca.replay.run_rca_graph", lambda city_id, dt, settings=None, client_factory=None: fake_result)

    fake_review = ReplayReview(
        eval_score=0.8,
        eval_passed=True,
        alignment_score=0.7,
        alignment_label="aligned",
        pros=["Good."],
        cons=["Evidence is thin.", "Confidence over-stated."],
        improvements=["More rounds."],
        reviewer_comment="Stub.",
    )
    monkeypatch.setattr("rca.replay.review_outcome", lambda **kwargs: fake_review)
    monkeypatch.setattr("rca.replay.store_replay_review", lambda **kwargs: None)

    summary = simulate_city(0, client_factory=lambda _: None)

    con_texts = [text for text, _ in summary.top_cons]
    assert "Evidence is thin." in con_texts


def test_simulate_city_no_signal_dates_returns_empty_summary(monkeypatch):
    from rca.replay import simulate_city

    monkeypatch.setattr("rca.replay.find_signal_dates", lambda city_id: [])
    monkeypatch.setattr("rca.replay.reset_city_state", lambda city_id: {})

    summary = simulate_city(0)

    assert summary.total_dates == 0
    assert summary.passed_count == 0
    assert summary.avg_eval_score == 0.0
    assert summary.avg_alignment_score is None
