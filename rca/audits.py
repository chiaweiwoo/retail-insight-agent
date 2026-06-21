"""Deterministic evaluation checks for RCA output.

Phase 2: stub that always passes. Phase 3 will wire in the real checks.
"""
from __future__ import annotations

from typing import Any

from rca.state import EvaluationResult


def run_evaluation(
    decision_brief: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
) -> EvaluationResult:
    return EvaluationResult(passed=True, score=1.0)
