"""Tests for the alignment reviewer module."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from rca.reviewer import ReplayReview, _extract_json_object, _failed_check_summary, review_outcome
from rca.stubclient import stub_client_factory

_BRIEF = {
    "headline": "Sales drop driven by inventory pressure.",
    "confidence": "low",
    "situation": "City 0 recorded a drop vs baseline.",
    "business_impact": "Normalized sales below baseline.",
    "most_likely_explanation": "Stockout pressure during peak hours reduced demand.",
    "recommended_action": "Review replenishment schedule.",
    "owner_function": "Operations",
    "urgency": "medium",
    "expected_benefit": "Reduce recurrence risk.",
    "monitoring_plan": {
        "metrics_to_watch": ["stockout_product_rate"],
        "review_horizon": "7 days",
        "escalation_trigger": "Drop repeats.",
    },
    "unknowns": ["Margin data unavailable."],
    "caveats": ["Synthetic goals for screening only."],
    "evidence_summary": ["Stockout pressure present."],
    "alternatives": ["No strong external event."],
}

_EVIDENCE = [
    {"id": "ev_001", "evidence_type": "inference", "summary": "Stockout present"},
    {"id": "ev_002", "evidence_type": "observation", "summary": "Sales below target"},
]

_STUB_SETTINGS = MagicMock()
_STUB_SETTINGS.api_key = "stub"
_STUB_SETTINGS.base_url = "stub"
_STUB_SETTINGS.model = "stub"
_STUB_SETTINGS.thinking_enabled = False


@pytest.fixture(autouse=True)
def _patch_supabase(monkeypatch):
    fake = MagicMock()
    fake.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[])
    monkeypatch.setattr("rca.reviewer.make_supabase_schema_client", lambda schema=None: fake)


# ── _extract_json_object ──────────────────────────────────────────────────────


def test_extract_json_object_clean():
    text = '{"a": 1, "b": "hello"}'
    result = _extract_json_object(text)
    assert result == {"a": 1, "b": "hello"}


def test_extract_json_object_with_surrounding_text():
    text = "Here is the result: {\"score\": 0.9} done."
    result = _extract_json_object(text)
    assert result["score"] == 0.9


def test_extract_json_object_invalid_returns_empty():
    result = _extract_json_object("not json at all")
    assert result == {}


# ── _failed_check_summary ─────────────────────────────────────────────────────


def test_failed_check_summary_all_passed():
    checks = [{"name": "foo", "passed": True, "severity": "high", "message": ""}]
    result = _failed_check_summary(checks)
    assert "All deterministic checks passed" in result


def test_failed_check_summary_one_failed():
    checks = [
        {"name": "no_currency_terms", "passed": False, "severity": "high", "message": "Currency found."},
        {"name": "headline_non_empty", "passed": True, "severity": "medium", "message": ""},
    ]
    result = _failed_check_summary(checks)
    assert "no_currency_terms" in result
    assert "Currency found" in result
    assert "headline_non_empty" not in result


# ── review_outcome with stub ──────────────────────────────────────────────────


def test_review_outcome_stub_returns_replay_review():
    from rca.llm import LLMSettings

    settings = LLMSettings(api_key="stub", base_url="stub", model="stub", thinking_enabled=False)
    result = review_outcome(
        decision_brief=_BRIEF,
        evidence_ledger=_EVIDENCE,
        decision_card_markdown="# Decision Card\n- headline: Sales drop",
        settings=settings,
        client_factory=stub_client_factory,
        run_id="test_run",
    )

    assert isinstance(result, ReplayReview)


def test_review_outcome_stub_eval_score_in_range():
    from rca.llm import LLMSettings

    settings = LLMSettings(api_key="stub", base_url="stub", model="stub", thinking_enabled=False)
    result = review_outcome(
        decision_brief=_BRIEF,
        evidence_ledger=_EVIDENCE,
        decision_card_markdown="# Decision Card",
        settings=settings,
        client_factory=stub_client_factory,
        run_id="test_run",
    )

    assert 0.0 <= result.eval_score <= 1.0


def test_review_outcome_stub_alignment_label_valid():
    from rca.llm import LLMSettings

    settings = LLMSettings(api_key="stub", base_url="stub", model="stub", thinking_enabled=False)
    result = review_outcome(
        decision_brief=_BRIEF,
        evidence_ledger=_EVIDENCE,
        decision_card_markdown="# Decision Card",
        settings=settings,
        client_factory=stub_client_factory,
        run_id="test_run",
    )

    assert result.alignment_label in {"aligned", "partial", "misaligned"}


def test_review_outcome_stub_has_pros_and_cons():
    from rca.llm import LLMSettings

    settings = LLMSettings(api_key="stub", base_url="stub", model="stub", thinking_enabled=False)
    result = review_outcome(
        decision_brief=_BRIEF,
        evidence_ledger=_EVIDENCE,
        decision_card_markdown="# Decision Card",
        settings=settings,
        client_factory=stub_client_factory,
        run_id="test_run",
    )

    assert isinstance(result.pros, list)
    assert isinstance(result.cons, list)
    assert isinstance(result.improvements, list)
    assert len(result.pros) >= 1


def test_review_outcome_stub_has_deterministic_checks():
    from rca.llm import LLMSettings

    settings = LLMSettings(api_key="stub", base_url="stub", model="stub", thinking_enabled=False)
    result = review_outcome(
        decision_brief=_BRIEF,
        evidence_ledger=_EVIDENCE,
        decision_card_markdown="# Decision Card",
        settings=settings,
        client_factory=stub_client_factory,
        run_id="test_run",
    )

    assert len(result.deterministic_checks) == 8


def test_review_outcome_fallback_on_broken_llm():
    """When the LLM client raises, reviewer falls back to partial defaults."""
    from rca.llm import LLMSettings

    def broken_factory(node_name):
        client = MagicMock()
        client.chat.completions.create.side_effect = RuntimeError("LLM down")
        return client

    settings = LLMSettings(api_key="x", base_url="x", model="x", thinking_enabled=False)
    result = review_outcome(
        decision_brief=_BRIEF,
        evidence_ledger=_EVIDENCE,
        decision_card_markdown="# Decision Card",
        settings=settings,
        client_factory=broken_factory,
        run_id="test_run",
    )

    assert result.alignment_label == "partial"
    assert 0.0 <= result.alignment_score <= 1.0
