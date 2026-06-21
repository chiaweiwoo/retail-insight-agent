"""LLM alignment reviewer for RCA output quality assessment.

Combines the Phase 3 deterministic audits with an LLM alignment judge that
scores each outcome against the project's core guardrails and management
usefulness criteria.

The LLM judge runs by default. Tests can inject the stub client directly.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from rca.audits import run_evaluation
from rca.config import TABLE_SIMULATE_REVIEW, current_timestamp_sgt_iso, make_supabase_schema_client
from rca.llm import ClientFactory, LLMSettings, make_routed_settings

# ── Prompt ────────────────────────────────────────────────────────────────────

REVIEWER_ALIGNMENT_PROMPT = """\
You are a quality reviewer for retail RCA (root cause analysis) outputs.
Your job is to assess how well an RCA decision brief aligns with the project's core guardrails and usefulness criteria.

## Core guardrails (hard rules)
1. Output must stay at city/date grain. No product identifiers, SKU numbers, or store numbers in root cause claims.
2. sale_amount and hours_sale are normalized amounts, not currency. No dollar signs, USD, CNY, or computed revenue/profit/margin figures.
3. Internal Supabase facts are the primary evidence source. External/news evidence is supportive only.
4. Confidence must be calibrated to evidence volume. High confidence requires substantial internal evidence.
5. "Insufficient evidence" and "unknown" are valid, encouraged outcomes. Do not force a root cause.

## Usefulness criteria (soft rules)
6. The recommended action must be specific and actionable for the named owner function.
7. The monitoring plan must specify concrete metrics to watch, not vague outcomes.
8. Evidence claims must be traceable — not fabricated from the signal alone.
9. Caveats must acknowledge data limitations honestly (unlabeled activity_flag, inferred holiday names, synthetic goals).

## Output format
Return ONLY valid JSON — no prose, no markdown, no explanation before or after.
Use exactly these fields:
{
  "alignment_score": <float 0.0–1.0, 1.0 = fully aligned>,
  "alignment_label": <"aligned" | "partial" | "misaligned">,
  "pros": [<2–4 specific strengths, each a short sentence>],
  "cons": [<2–4 specific violations or weaknesses; each must quote or paraphrase a specific claim from the supplied brief or evidence — not a general quality concern>],
  "improvements": [<2–4 concrete suggestions, each a short sentence>],
  "comment": <one-sentence overall verdict>
}

Only assess what is present in the supplied brief and evidence ledger.
Do not invent problems or praise that are not grounded in the supplied input.

Scoring guidance:
- aligned   (0.75–1.00): respects all hard guardrails, useful output
- partial   (0.40–0.74): minor guardrail issues or thin but honest output
- misaligned (0.00–0.39): violates a hard guardrail or is misleadingly confident
If a criterion is not applicable to this brief, omit it from cons rather than forcing a finding.
"""

# ── Data types ────────────────────────────────────────────────────────────────


@dataclass
class SimulateReview:
    eval_score: float
    eval_passed: bool
    alignment_score: float
    alignment_label: str
    pros: list[str]
    cons: list[str]
    improvements: list[str]
    reviewer_comment: str
    deterministic_checks: list[dict[str, Any]] = field(default_factory=list)


# ── LLM alignment judge ───────────────────────────────────────────────────────


def _extract_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return {}
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        return {}


def _failed_check_summary(deterministic_checks: list[dict[str, Any]]) -> str:
    failed = [c for c in deterministic_checks if not c.get("passed")]
    if not failed:
        return "All deterministic checks passed."
    lines = ["Failed deterministic checks:"]
    for c in failed:
        lines.append(f"  - [{c['severity']}] {c['name']}: {c.get('message', '')}")
    return "\n".join(lines)


def _run_alignment_judge(
    *,
    decision_brief: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
    decision_card_markdown: str,
    deterministic_checks: list[dict[str, Any]],
    settings: LLMSettings,
    client_factory: ClientFactory,
) -> dict[str, Any]:
    routed = make_routed_settings(settings, "reviewer")
    client = client_factory("reviewer")

    evidence_count = len(evidence_ledger)
    inference_count = sum(1 for ev in evidence_ledger if ev.get("evidence_type") == "inference")
    external_count = sum(1 for ev in evidence_ledger if ev.get("evidence_type") == "external")

    user_message = (
        f"## Decision Brief (JSON)\n{json.dumps(decision_brief, ensure_ascii=False, indent=2)}\n\n"
        f"## Decision Card (Markdown)\n{decision_card_markdown}\n\n"
        f"## Evidence Summary\n"
        f"Total items: {evidence_count} | Inference: {inference_count} | External: {external_count}\n\n"
        f"## Deterministic Audit Results\n{_failed_check_summary(deterministic_checks)}\n\n"
        "Review this RCA output against the guardrails and return valid JSON only."
    )

    try:
        response = client.chat.completions.create(
            model=routed.model,
            messages=[
                {"role": "system", "content": REVIEWER_ALIGNMENT_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content or ""
        parsed = _extract_json_object(content)
    except Exception:
        parsed = {}

    alignment_score = float(parsed.get("alignment_score") or 0.5)
    alignment_label = str(parsed.get("alignment_label") or "partial")
    if alignment_label not in {"aligned", "partial", "misaligned"}:
        alignment_label = "partial"

    return {
        "alignment_score": round(alignment_score, 4),
        "alignment_label": alignment_label,
        "pros": list(parsed.get("pros") or []),
        "cons": list(parsed.get("cons") or []),
        "improvements": list(parsed.get("improvements") or []),
        "comment": str(parsed.get("comment") or "Reviewer parse error — defaulting to partial."),
    }


# ── Public API ────────────────────────────────────────────────────────────────


def review_outcome(
    *,
    decision_brief: dict[str, Any],
    evidence_ledger: list[dict[str, Any]],
    decision_card_markdown: str,
    settings: LLMSettings,
    client_factory: ClientFactory,
    run_id: str,
) -> SimulateReview:
    eval_result = run_evaluation(decision_brief, evidence_ledger)
    det_checks = [c.model_dump(mode="json") for c in eval_result.deterministic_checks]

    alignment = _run_alignment_judge(
        decision_brief=decision_brief,
        evidence_ledger=evidence_ledger,
        decision_card_markdown=decision_card_markdown,
        deterministic_checks=det_checks,
        settings=settings,
        client_factory=client_factory,
    )

    return SimulateReview(
        eval_score=eval_result.score,
        eval_passed=eval_result.passed,
        alignment_score=alignment["alignment_score"],
        alignment_label=alignment["alignment_label"],
        pros=alignment["pros"],
        cons=alignment["cons"],
        improvements=alignment["improvements"],
        reviewer_comment=alignment["comment"],
        deterministic_checks=det_checks,
    )


def store_simulate_review(
    *,
    batch_id: str,
    run_id: str,
    city_id: int,
    dt: str,
    signal_label: str,
    review: SimulateReview,
) -> None:
    client = make_supabase_schema_client()
    try:
        client.table(TABLE_SIMULATE_REVIEW).insert(
            {
                "batch_id": batch_id,
                "run_id": run_id,
                "city_id": city_id,
                "dt": dt,
                "signal_label": signal_label,
                "eval_score": review.eval_score,
                "eval_passed": review.eval_passed,
                "alignment_score": review.alignment_score,
                "alignment_label": review.alignment_label,
                "pros": review.pros,
                "cons": review.cons,
                "improvements": review.improvements,
                "reviewer_comment": review.reviewer_comment,
                "deterministic_checks": review.deterministic_checks,
                "created_at": current_timestamp_sgt_iso(),
            }
        ).execute()
    except Exception:
        return
