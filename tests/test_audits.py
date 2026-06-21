"""Tests for the 8 deterministic audit checks and run_evaluation."""
from __future__ import annotations

import pytest

from rca.audits import (
    check_confidence_calibration,
    check_evidence_non_empty,
    check_external_not_sole_source,
    check_headline_non_empty,
    check_monitoring_plan_populated,
    check_no_currency_terms,
    check_no_product_store_root_cause,
    check_unknowns_when_thin_evidence,
    run_evaluation,
)


# ── Helpers ────────────────────────────────────────────────────────────────────


def _brief(**overrides) -> dict:
    """Return a minimal valid decision brief with all required fields set to passing defaults."""
    base = {
        "headline": "Sales drop driven by inventory pressure.",
        "confidence": "low",
        "situation": "City 0 recorded a drop vs baseline.",
        "business_impact": "Normalized sales below baseline.",
        "most_likely_explanation": "Stockout pressure during peak hours reduced demand.",
        "recommended_action": "Review replenishment schedule for the affected category.",
        "owner_function": "Operations",
        "urgency": "medium",
        "expected_benefit": "Reduce recurrence risk.",
        "monitoring_plan": {
            "metrics_to_watch": ["stockout_product_rate"],
            "review_horizon": "7 days",
            "escalation_trigger": "Drop repeats on next same-weekday cycle.",
        },
        "unknowns": ["Margin data is unavailable."],
        "caveats": ["Synthetic goals are used for screening only."],
        "evidence_summary": ["Stockout pressure is present."],
        "alternatives": ["No strong external event found."],
    }
    base.update(overrides)
    return base


def _evidence(n: int, evidence_type: str = "inference") -> list[dict]:
    return [
        {"id": f"ev_{i:03d}", "evidence_type": evidence_type, "summary": f"Evidence item {i}"}
        for i in range(1, n + 1)
    ]


# ── check_no_currency_terms ───────────────────────────────────────────────────


def test_no_currency_terms_passes_clean_brief():
    result = check_no_currency_terms(_brief())
    assert result.passed
    assert result.severity == "high"


def test_no_currency_terms_fails_dollar_sign():
    brief = _brief(situation="Sales were $1200 below baseline.")
    result = check_no_currency_terms(brief)
    assert not result.passed
    assert "$" in result.message or "Currency" in result.message


def test_no_currency_terms_fails_usd():
    brief = _brief(business_impact="Total impact exceeds USD threshold.")
    result = check_no_currency_terms(brief)
    assert not result.passed


def test_no_currency_terms_fails_revenue_with_number():
    brief = _brief(most_likely_explanation="Revenue of 5000 was lost due to stockouts.")
    result = check_no_currency_terms(brief)
    assert not result.passed


def test_no_currency_terms_passes_word_revenue_without_figure():
    brief = _brief(most_likely_explanation="Revenue trends suggest inventory pressure.")
    result = check_no_currency_terms(brief)
    assert result.passed


# ── check_no_product_store_root_cause ────────────────────────────────────────


def test_no_product_store_root_cause_passes_city_level_explanation():
    result = check_no_product_store_root_cause(_brief())
    assert result.passed
    assert result.severity == "high"


def test_no_product_store_root_cause_fails_product_in_explanation():
    brief = _brief(most_likely_explanation="Product 123 ran out during peak hours.")
    result = check_no_product_store_root_cause(brief)
    assert not result.passed
    assert "product" in result.message.lower() or "store" in result.message.lower()


def test_no_product_store_root_cause_fails_store_in_recommended_action():
    brief = _brief(recommended_action="Restock store 5 first.")
    result = check_no_product_store_root_cause(brief)
    assert not result.passed


def test_no_product_store_root_cause_passes_follow_up_framing():
    brief = _brief(most_likely_explanation="Stockout rates are high city-wide; product-level detail is unavailable at runtime.")
    result = check_no_product_store_root_cause(brief)
    assert result.passed


# ── check_evidence_non_empty ──────────────────────────────────────────────────


def test_evidence_non_empty_passes_with_evidence():
    result = check_evidence_non_empty(_evidence(3))
    assert result.passed
    assert result.severity == "medium"


def test_evidence_non_empty_fails_with_empty_ledger():
    result = check_evidence_non_empty([])
    assert not result.passed
    assert "empty" in result.message.lower()


# ── check_headline_non_empty ──────────────────────────────────────────────────


def test_headline_non_empty_passes_specific_headline():
    result = check_headline_non_empty(_brief())
    assert result.passed
    assert result.severity == "medium"


def test_headline_non_empty_fails_empty_string():
    result = check_headline_non_empty(_brief(headline=""))
    assert not result.passed


def test_headline_non_empty_fails_none():
    result = check_headline_non_empty(_brief(headline=None))
    assert not result.passed


def test_headline_non_empty_fails_fallback_prefix():
    result = check_headline_non_empty(_brief(headline="Decision brief parsing failed for city 0"))
    assert not result.passed
    assert "fallback" in result.message.lower() or "parsed" in result.message.lower()


# ── check_confidence_calibration ─────────────────────────────────────────────


def test_confidence_calibration_passes_low_with_one_item():
    result = check_confidence_calibration(_brief(confidence="low"), _evidence(1))
    assert result.passed


def test_confidence_calibration_passes_high_with_five_items():
    result = check_confidence_calibration(_brief(confidence="high"), _evidence(5))
    assert result.passed


def test_confidence_calibration_fails_high_with_two_items():
    result = check_confidence_calibration(_brief(confidence="high"), _evidence(2))
    assert not result.passed
    assert "high" in result.message.lower()
    assert result.severity == "medium"


def test_confidence_calibration_fails_medium_with_zero_inference():
    ev = _evidence(3, evidence_type="observation")
    result = check_confidence_calibration(_brief(confidence="medium"), ev)
    assert not result.passed
    assert "medium" in result.message.lower()


def test_confidence_calibration_passes_medium_with_two_inference():
    ev = _evidence(2, evidence_type="inference")
    result = check_confidence_calibration(_brief(confidence="medium"), ev)
    assert result.passed


# ── check_unknowns_when_thin_evidence ────────────────────────────────────────


def test_unknowns_thin_evidence_passes_with_enough_evidence():
    result = check_unknowns_when_thin_evidence(_brief(unknowns=[]), _evidence(5))
    assert result.passed
    assert result.severity == "low"


def test_unknowns_thin_evidence_passes_thin_but_unknowns_present():
    brief = _brief(unknowns=["Margin data unavailable."])
    result = check_unknowns_when_thin_evidence(brief, _evidence(1))
    assert result.passed


def test_unknowns_thin_evidence_fails_thin_and_no_unknowns():
    brief = _brief(unknowns=[])
    result = check_unknowns_when_thin_evidence(brief, _evidence(2))
    assert not result.passed
    assert "thin" in result.message.lower() or "unknown" in result.message.lower()


def test_unknowns_thin_evidence_passes_exactly_three():
    brief = _brief(unknowns=[])
    result = check_unknowns_when_thin_evidence(brief, _evidence(3))
    assert result.passed


# ── check_external_not_sole_source ───────────────────────────────────────────


def test_external_not_sole_source_passes_mixed_types():
    ev = [
        {"id": "ev_001", "evidence_type": "observation", "summary": "internal"},
        {"id": "ev_002", "evidence_type": "external", "summary": "news"},
    ]
    result = check_external_not_sole_source(ev)
    assert result.passed
    assert result.severity == "medium"


def test_external_not_sole_source_passes_empty_ledger():
    result = check_external_not_sole_source([])
    assert result.passed


def test_external_not_sole_source_fails_all_external():
    ev = _evidence(3, evidence_type="external")
    result = check_external_not_sole_source(ev)
    assert not result.passed
    assert "external" in result.message.lower()


# ── check_monitoring_plan_populated ──────────────────────────────────────────


def test_monitoring_plan_passes_with_metrics():
    result = check_monitoring_plan_populated(_brief())
    assert result.passed
    assert result.severity == "low"


def test_monitoring_plan_fails_empty_metrics():
    brief = _brief(monitoring_plan={"metrics_to_watch": [], "review_horizon": "7 days", "escalation_trigger": ""})
    result = check_monitoring_plan_populated(brief)
    assert not result.passed
    assert "metrics" in result.message.lower()


def test_monitoring_plan_fails_missing_monitoring_plan():
    brief = _brief(monitoring_plan=None)
    result = check_monitoring_plan_populated(brief)
    assert not result.passed


def test_monitoring_plan_passes_non_dict_with_items():
    brief = _brief(monitoring_plan={"metrics_to_watch": ["stockout_product_rate", "sales_total"]})
    result = check_monitoring_plan_populated(brief)
    assert result.passed


# ── run_evaluation (composite) ────────────────────────────────────────────────


def test_run_evaluation_perfect_brief_scores_one():
    ev = _evidence(5)
    result = run_evaluation(_brief(), ev)
    assert result.passed
    assert result.score == 1.0
    assert len(result.deterministic_checks) == 8
    assert all(c.passed for c in result.deterministic_checks)


def test_run_evaluation_currency_in_brief_deducts_high():
    brief = _brief(headline="Revenue of $500 was lost.")
    result = run_evaluation(brief, _evidence(5))
    assert result.score == pytest.approx(1.0 - 0.25)
    assert result.passed


def test_run_evaluation_two_medium_failures_deduct_point_two():
    brief = _brief(headline="", confidence="high")
    ev = _evidence(2)
    result = run_evaluation(brief, ev)
    # headline_non_empty (medium, -0.10) + confidence_calibration (medium, -0.10) = 0.80
    assert result.score == pytest.approx(0.80)
    assert result.passed


def test_run_evaluation_fails_below_half():
    brief = _brief(
        headline="",
        most_likely_explanation="Store 1 and product 999 caused the drop. Revenue of $5000 lost.",
        monitoring_plan=None,
        unknowns=[],
    )
    ev = _evidence(1, evidence_type="external")
    result = run_evaluation(brief, ev)
    # currency (high -0.25) + product/store (high -0.25) + headline (medium -0.10)
    # + external-sole-source (medium -0.10) + monitoring (low -0.05) + unknowns-thin (low -0.05)
    # = 1.0 - 0.80 = 0.20
    assert result.score < 0.5
    assert not result.passed


def test_run_evaluation_llm_judge_disabled_by_default():
    result = run_evaluation(_brief(), _evidence(5))
    assert not result.llm_judge.enabled


def test_run_evaluation_returns_eight_checks():
    result = run_evaluation(_brief(), _evidence(5))
    check_names = {c.name for c in result.deterministic_checks}
    expected = {
        "no_currency_terms",
        "no_product_store_root_cause",
        "evidence_non_empty",
        "headline_non_empty",
        "confidence_calibration",
        "unknowns_when_thin_evidence",
        "external_not_sole_source",
        "monitoring_plan_populated",
    }
    assert check_names == expected
