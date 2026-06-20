"""Deterministic stub LLM client for --dry-run and tests.

Returns canned, well-formed responses per node — no network, no API key.
Used as the client_factory in run_coordinator(dry_run=True) and in unit tests.
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Canned response text per node name
# Will be updated in Phase 3 to include the Assessment block in analyst memos.
# ---------------------------------------------------------------------------

_ANALYST_MEMO_TEMPLATE = """\
## Scope
Store {store} on {dt} — {focus}.

## Findings
No anomalies detected in the {domain} domain during this dry-run.
Key figure: baseline 1000, observed 800 (-20%).

## Caveats
Stub response only — no real data was queried.

## Assessment
- verdict: inconclusive
- confidence: low
- key_numbers: baseline 1000, observed 800, delta -20%
- causal_caveat: correlation only — no causal inference possible from stub data
- data_gaps: all data gaps present; this is a dry-run stub
"""

_STUB_RESPONSES: dict[str, str] = {
    "sales_analyst": _ANALYST_MEMO_TEMPLATE.format(
        store="{store}", dt="{dt}", focus="sales performance", domain="sales"
    ),
    "ops_analyst": _ANALYST_MEMO_TEMPLATE.format(
        store="{store}", dt="{dt}", focus="operations / stockout", domain="operations"
    ),
    "commercial_analyst": _ANALYST_MEMO_TEMPLATE.format(
        store="{store}", dt="{dt}", focus="commercial / discount", domain="commercial"
    ),
    "market_analyst": _ANALYST_MEMO_TEMPLATE.format(
        store="{store}", dt="{dt}", focus="market context", domain="market"
    ),
    "research_analyst": """\
## Scope
External news search (dry-run — no real search performed).

## Findings
No relevant external events found in stub mode.

## Caveats
Stub response only.

## Assessment
- verdict: inconclusive
- confidence: low
- key_numbers: n/a
- causal_caveat: n/a
- data_gaps: web search not executed in dry-run mode
""",
    "critic": """\
## Critic Review

### Claim audit
- sales_analyst — verdict: keep (well-supported in stub)
- ops_analyst — verdict: needs_evidence (stockout data not conclusive)
- commercial_analyst — verdict: flag_correlational (discount correlation not causal)
- market_analyst — verdict: keep (context consistent with fleet-wide pattern)
- research_analyst — verdict: needs_evidence (no external data in dry-run)

### Gaps
- No margin data available
- External events unverifiable in stub mode

### Calibration note
Confidence levels are appropriate given stub evidence quality.
""",
    "coordinator_analyst": """\
## Trigger
A -20% trailing-7d sales drop was recorded at the store on the analysis date.

## Likely Drivers
1. [inconclusive / low] Possible stockout pressure — ops analyst found ambiguous signal
2. [inconclusive / low] Commercial activity present but correlation not causal

## Evidence
- Sales signal: -20% vs trailing 7-day baseline (stub figure)
- Critic note: stockout claim needs evidence; discount is correlational

## What we might be wrong about
- Critic flagged the discount–drop link as correlational, not causal
- External events unverified (dry-run)

## Caveats
All figures are stub values. No real data was queried in dry-run mode.

## Suggested Next Checks
- Confirm stockout hours from ops data
- Verify whether discount depth increased on the trigger date
""",
    "finance_controller": """\
## Finance Controller Note

**Materiality:** -20% trailing-7d drop (stub). This represents approximately 1.4x the store's
typical day-to-day variance — immaterial at fleet level, but worth monitoring for recurrence.
Note: all figures are normalized sales amounts, not currency.

**Margin risk:** Promotional activity present. Volume does not equal value — if the drop was
driven by discount depth, margin dilution is possible. Margin and cost data are unavailable;
flag for finance review if recurrence is confirmed.

**One-off vs structural:** Single-day trigger in stub mode. Insufficient history to classify
as structural. Recommend watching the next 5 trading days before drawing a conclusion.
""",
    "reflect": """\
## Reflection

- Weakest assumption: the -20% drop is attributed to stockout pressure, but the causal direction is ambiguous — a demand-side drop can precede stockouts as easily as cause them. Confirming would require intraday replenishment logs or demand forecasts not in this dataset.
- Missing data: no cost, margin, or intraday order data available; the ops analyst correctly flagged this but the synthesis treated the stockout correlation as more causal than warranted.
- Action implication: the "monitor" recommendation is appropriate given the uncertainty; escalation would require at least one additional day of stockout confirmation before it is justified.
""",
    "evaluator": """\
{"groundedness": 4, "calibration": 4, "actionability": 3, "conciseness": 4, "causal_honesty": 4, "summary": "Stub evaluation only."}
""",
    "story_writer": """\
# Story Report: h555 on 2024-05-16

## Executive Takeaway
The system ends with a low-confidence but readable decision: the drop is real, stockout pressure is plausible, and the next action is to validate operations before escalating.

## Why This Day Triggered Review
Sales fell enough versus the trailing seven-day baseline to cross the configured drop threshold, so the workflow opened a full RCA run.

## How The Analysis Unfolded
The sales analyst confirmed the signal with `get_signal_evidence` and `get_sales_context`. The ops analyst used `get_stockout_context` to test whether availability was part of the story. The commercial analyst checked promotions and discounts, while the market analyst looked at calendar, weather, and peer context.

## Where The System Challenged Itself
The critic pushed back on overconfident claims, especially where the analysts tried to turn correlation into proof or where no baseline was available.

## Final Decision
The final card keeps the tone restrained: monitor, validate stockout baseline, and avoid escalation until the operational hypothesis is better supported.
""",
    "slt_brief": "__dynamic__",
}


# ---------------------------------------------------------------------------
# Stub client objects — mimic the openai SDK's response structure
# ---------------------------------------------------------------------------


class _StubMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_calls = None


class _StubChoice:
    def __init__(self, content: str) -> None:
        self.message = _StubMessage(content)


class _StubResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_StubChoice(content)]


class _StubCompletions:
    def __init__(self, node_name: str) -> None:
        self._node_name = node_name

    def create(self, **kwargs: Any) -> _StubResponse:
        messages = kwargs.get("messages") or []
        store, dt = _extract_store_and_dt(messages)
        template = _STUB_RESPONSES.get(self._node_name, _default_stub(self._node_name))
        if self._node_name == "slt_brief":
            content = _build_slt_stub(messages, store, dt)
        elif self._node_name == "evaluator":
            content = template
        else:
            content = template.format(store=store, dt=dt)
        return _StubResponse(content)


class _StubChat:
    def __init__(self, node_name: str) -> None:
        self.completions = _StubCompletions(node_name)


class StubClient:
    """Drop-in replacement for the OpenAI client in dry-run mode."""

    def __init__(self, node_name: str) -> None:
        self.chat = _StubChat(node_name)


def _default_stub(node_name: str) -> str:
    return (
        f"## Scope\n{node_name} (stub)\n\n## Findings\nDry-run stub.\n\n## Caveats\nNone.\n\n"
        f"## Assessment\n- verdict: inconclusive\n- confidence: low\n"
        f"- key_numbers: n/a\n- causal_caveat: n/a\n- data_gaps: dry-run\n"
    )


def _extract_store_and_dt(messages: list[dict[str, Any]]) -> tuple[str, str]:
    for message in reversed(messages):
        content = message.get("content")
        if not isinstance(content, str):
            continue
        match = re.search(r"store\s+([a-z]\d+)\s+on\s+(\d{4}-\d{2}-\d{2})", content, re.IGNORECASE)
        if match:
            return match.group(1), match.group(2)
    return "unknown_store", "unknown_date"


def _build_slt_stub(messages: list[dict[str, Any]], store: str, dt: str) -> str:
    previous_trigger_count = 0
    for message in reversed(messages):
        content = message.get("content")
        if not isinstance(content, str):
            continue
        match = re.search(r'"previous_trigger_count"\s*:\s*(\d+)', content)
        if match:
            previous_trigger_count = int(match.group(1))
            break
    pattern = (
        f"recurring — {previous_trigger_count} prior RCA outcome(s) for this store"
        if previous_trigger_count > 0
        else "first observed — no prior RCA history for this store"
    )
    return f"""\
## Decision Card — {store} {dt}
- headline: Low confidence: inconclusive sales drop; insufficient evidence to identify primary driver
- confidence: low
- materiality: immaterial / noise — single store-day, ~1.4x daily variance estimated exposure (stub)
- pattern: {pattern}
- action: none — monitor next 5 trading days
- escalate: no
"""


def stub_client_factory(node_name: str) -> StubClient:
    """Return a StubClient for the given node name. Use as client_factory in run_coordinator."""
    return StubClient(node_name)
