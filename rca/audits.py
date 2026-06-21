"""Deterministic evaluation checks for RCA output.

Eight rule-based checks enforce the hard constraints the agent must never violate.
Each check returns a DeterministicCheck. run_evaluation assembles them into an
EvaluationResult with a 0-to-1 score.

Scoring deductions per failed check:
  high   severity → -0.25
  medium severity → -0.10
  low    severity → -0.05

passed = score >= 0.5
"""
from __future__ import annotations

import re
from typing import Any

from rca.state import DeterministicCheck, EvaluationResult, LlmJudgeResult

_SEVERITY_WEIGHTS: dict[str, float] = {"high": 0.25, "medium": 0.10, "low": 0.05}

# ── Pattern sets ──────────────────────────────────────────────────────────────

_CURRENCY_RE = re.compile(
    r"\$\s*\d"                                              # $100 / $ 100
    r"|\busd\b"                                             # USD
    r"|\bcny\b"                                             # CNY
    r"|\b(?:revenue|profit|margin)\s+(?:of|is|was|at|:)\s*[\$\d]",  # revenue of 1234
    re.IGNORECASE,
)

_PRODUCT_STORE_CAUSE_RE = re.compile(
    r"\b(?:product|sku)\s+(?:#|id\s+)?[0-9a-z_-]+"        # "product 123", "sku ABC"
    r"|\bstore\s+(?:#|id\s+)?[0-9]+"                       # "store 5", "store #12"
    r"|\bstore[_-]\d+"                                      # "store_5"
    r"|\b(?:product|store)\s+level\s+(?:root\s+cause|drove|caused|is\s+responsible)",
    re.IGNORECASE,
)


# ── Helper ────────────────────────────────────────────────────────────────────


def _brief_full_text(brief: dict[str, Any]) -> str:
    """Concatenate all narrative text fields for pattern scanning."""
    fields = [
        "headline", "situation", "business_impact",
        "most_likely_explanation", "recommended_action", "expected_benefit",
    ]
    parts = [str(brief.get(f) or "") for f in fields]
    for item in (brief.get("evidence_summary") or []):
        parts.append(str(item))
    for item in (brief.get("unknowns") or []):
        parts.append(str(item))
    for item in (brief.get("caveats") or []):
        parts.append(str(item))
    for item in (brief.get("alternatives") or []):
        parts.append(str(item))
    return " ".join(parts)


# ── Deterministic checks (8) ──────────────────────────────────────────────────


def check_no_currency_terms(brief: dict[str, Any]) -> DeterministicCheck:
    """sale_amount is normalized — dollar signs, USD, CNY, and computed revenue/profit/margin are forbidden."""
    text = _brief_full_text(brief)
    match = _CURRENCY_RE.search(text)
    return DeterministicCheck(
        name="no_currency_terms",
        passed=match is None,
        severity="high",
        message=(
            ""
            if match is None
            else f"Currency term found: '{match.group(0).strip()}'. "
            "sale_amount is a normalized amount, not currency. Remove dollar signs and computed currency figures."
        ),
    )


def check_no_product_store_root_cause(brief: dict[str, Any]) -> DeterministicCheck:
    """Root cause must stay at city/date grain — no product or store identifiers in causal claims."""
    text = (str(brief.get("most_likely_explanation") or "") + " " + str(brief.get("recommended_action") or ""))
    match = _PRODUCT_STORE_CAUSE_RE.search(text)
    return DeterministicCheck(
        name="no_product_store_root_cause",
        passed=match is None,
        severity="high",
        message=(
            ""
            if match is None
            else f"Product or store identifier in causal claim: '{match.group(0).strip()}'. "
            "Runtime evidence is city/date only. Reframe as a follow-up data need."
        ),
    )


def check_evidence_non_empty(evidence_ledger: list[dict[str, Any]]) -> DeterministicCheck:
    """At least one evidence item must be in the ledger after investigation."""
    passed = len(evidence_ledger) >= 1
    return DeterministicCheck(
        name="evidence_non_empty",
        passed=passed,
        severity="medium",
        message="" if passed else "Evidence ledger is empty. Investigation ran but produced no traceable evidence.",
    )


def check_headline_non_empty(brief: dict[str, Any]) -> DeterministicCheck:
    """Headline must be a specific, non-fallback string."""
    headline = str(brief.get("headline") or "").strip()
    is_fallback = headline.lower().startswith("decision brief parsing failed")
    passed = bool(headline) and not is_fallback
    return DeterministicCheck(
        name="headline_non_empty",
        passed=passed,
        severity="medium",
        message="" if passed else "Headline is empty or is a generic fallback. Coordinator output was not parsed.",
    )


def check_confidence_calibration(
    brief: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
) -> DeterministicCheck:
    """Confidence level must be backed by an appropriate number of inference evidence items."""
    confidence = str(brief.get("confidence") or "low")
    inference_count = sum(1 for ev in evidence_ledger if ev.get("evidence_type") == "inference")

    if confidence == "high" and inference_count < 5:
        return DeterministicCheck(
            name="confidence_calibration",
            passed=False,
            severity="medium",
            message=(
                f"Confidence is 'high' but only {inference_count} inference item(s) found "
                "(requires ≥5). Lower confidence or gather more evidence."
            ),
        )
    if confidence == "medium" and inference_count < 2:
        return DeterministicCheck(
            name="confidence_calibration",
            passed=False,
            severity="medium",
            message=(
                f"Confidence is 'medium' but only {inference_count} inference item(s) found "
                "(requires ≥2). Lower confidence to 'low' or gather more evidence."
            ),
        )
    return DeterministicCheck(name="confidence_calibration", passed=True, severity="medium")


def check_unknowns_when_thin_evidence(
    brief: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
) -> DeterministicCheck:
    """With fewer than 3 evidence items the brief must acknowledge unknowns."""
    unknowns = list(brief.get("unknowns") or [])
    n = len(evidence_ledger)
    if n < 3 and not unknowns:
        return DeterministicCheck(
            name="unknowns_when_thin_evidence",
            passed=False,
            severity="low",
            message=(
                f"Only {n} evidence item(s) but unknowns list is empty. "
                "Thin evidence requires explicit acknowledgment of what is not known."
            ),
        )
    return DeterministicCheck(name="unknowns_when_thin_evidence", passed=True, severity="low")


def check_external_not_sole_source(evidence_ledger: list[dict[str, Any]]) -> DeterministicCheck:
    """Internal Supabase facts must be present; external evidence alone is not sufficient."""
    if not evidence_ledger:
        return DeterministicCheck(name="external_not_sole_source", passed=True, severity="medium")
    types = {ev.get("evidence_type") for ev in evidence_ledger}
    if types == {"external"}:
        return DeterministicCheck(
            name="external_not_sole_source",
            passed=False,
            severity="medium",
            message="All evidence items are type 'external'. Internal Supabase facts must be the primary source.",
        )
    return DeterministicCheck(name="external_not_sole_source", passed=True, severity="medium")


def check_monitoring_plan_populated(brief: dict[str, Any]) -> DeterministicCheck:
    """Decision brief must specify at least one metric to watch."""
    mp = brief.get("monitoring_plan") or {}
    metrics = list(mp.get("metrics_to_watch") or []) if isinstance(mp, dict) else []
    passed = bool(metrics)
    return DeterministicCheck(
        name="monitoring_plan_populated",
        passed=passed,
        severity="low",
        message="" if passed else "monitoring_plan.metrics_to_watch is empty. Specify what to monitor after this decision.",
    )


# ── Composite evaluation ──────────────────────────────────────────────────────


def run_evaluation(
    decision_brief: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
) -> EvaluationResult:
    """Run all 8 deterministic checks and compute a 0-to-1 quality score."""
    checks: list[DeterministicCheck] = [
        check_no_currency_terms(decision_brief),
        check_no_product_store_root_cause(decision_brief),
        check_evidence_non_empty(evidence_ledger),
        check_headline_non_empty(decision_brief),
        check_confidence_calibration(decision_brief, evidence_ledger),
        check_unknowns_when_thin_evidence(decision_brief, evidence_ledger),
        check_external_not_sole_source(evidence_ledger),
        check_monitoring_plan_populated(decision_brief),
    ]

    score = 1.0
    for check in checks:
        if not check.passed:
            score -= _SEVERITY_WEIGHTS.get(check.severity, 0.0)
    score = max(0.0, round(score, 4))

    return EvaluationResult(
        passed=score >= 0.5,
        score=score,
        deterministic_checks=checks,
        llm_judge=LlmJudgeResult(enabled=False),
    )
