from __future__ import annotations

from rca.report import (
    build_story_markdown,
    render_markdown_document,
    render_story_document,
    sanitize_generated_markdown,
)


def test_render_markdown_document_creates_html_shell() -> None:
    html = render_markdown_document("# Title\n\n- item", title="Demo")
    assert "<html" in html
    assert "<h1>Title</h1>" in html
    assert "<li>item</li>" in html
    assert "<title>Demo</title>" in html


def test_build_story_markdown_fallback_creates_layered_narrative() -> None:
    trace = {
        "store_alias": "h555",
        "dt": "2024-05-16",
        "planner": {
            "selected_analysts": ["sales_analyst", "ops_analyst"],
            "skipped_analysts": [{"analyst": "research_analyst", "reason": "gated off"}],
            "planning_inputs": {
                "signal_evidence": {
                    "metric": "trailing_7d_pct_change",
                    "signal_label": "drop",
                    "current_sales": 131.91,
                    "trailing_7d_avg_sales": 175.63,
                    "trailing_7d_pct_change": -24.9,
                }
            },
        },
        "decision_card_markdown": (
            "## Decision Card\n"
            "- headline: Sales dropped sharply\n"
            "- confidence: medium\n"
            "- materiality: low to moderate\n"
            "- pattern: possible stockout pressure\n"
            "- action: validate stockout baseline\n"
            "- escalate: no\n"
        ),
        "analyst_results": [
            {
                "name": "sales_analyst",
                "focus": "sales performance",
                "memo_markdown": (
                    "## Assessment\n"
                    "- verdict: inconclusive\n"
                    "- confidence: low\n"
                    "- key_numbers: 131.91 current sales, -24.9% vs trailing 7d\n"
                    "- causal_caveat: no causal data\n"
                    "- data_gaps: no ops data\n"
                ),
                "tool_calls": [
                    {"name": "get_signal_evidence"},
                    {"name": "get_sales_context"},
                ],
            }
        ],
        "critic_note_markdown": "## Claim Audit\n- keep the signal, downgrade the cause",
        "controller_note_markdown": "## Materiality\nLow to moderate.",
        "coordinator_report_markdown": "# RCA Report\n\n## Trigger\nDrop",
    }

    markdown_text = build_story_markdown(trace, use_llm=False)
    assert "## Executive Takeaway" in markdown_text
    assert "## How The Analysis Unfolded" in markdown_text
    assert "sales_analyst" in markdown_text
    assert "get_signal_evidence, get_sales_context" in markdown_text


def test_render_story_document_builds_structured_story_shell() -> None:
    markdown_text = """
## Executive Takeaway

**Store m041 hit 146.4 units on Sunday 2024-05-12 Ã¢â‚¬â€ its highest single-day sales in the 90-day dataset.**

**Action:** Check the raw transaction feed before changing operations.

## How The Analysis Unfolded

### Layer 1

**Evidence (confirmed)**:
- Signal math checks out
- Store ranked first in its prefix group
"""

    html = render_story_document(markdown_text, title="Story Report for m041 on 2024-05-12")
    assert 'class="story-hero"' in html
    assert 'class="story-section"' in html
    assert "<li>Signal math checks out</li>" in html
    assert "Ã¢â‚¬â€" not in html
    assert "Ã¢â€ â€™" not in html


def test_sanitize_generated_markdown_removes_units_revenue_and_tier_language() -> None:
    raw = (
        "Store m041 recorded unit sales and sales units. "
        "It sold 28.67 units. "
        "Typical daily revenue of $200. "
        "Ranked #1 among 'l' prefix group stores, tier 'm', and best in its tier. "
        "We also saw â€” and Â°C and â‰¤."
    )
    cleaned = sanitize_generated_markdown(raw)

    assert "unit sales" not in cleaned.lower()
    assert "sales units" not in cleaned.lower()
    assert "units" not in cleaned.lower()
    assert "28.67 sales amount" in cleaned.lower()

    assert "revenue" not in cleaned.lower()
    assert "200 sales amount" in cleaned.lower()
    assert "$" not in cleaned

    assert "tier" not in cleaned.lower()
    assert "store group L" in cleaned
    assert "store group M" in cleaned
    assert "'l' prefix group" not in cleaned.lower()

    assert "â€”" not in cleaned
    assert "Â°C" not in cleaned
    assert "â‰¤" not in cleaned


def test_find_report_language_issues_flags_forbidden_strings() -> None:
    from rca.report import find_report_language_issues
    text = "Here we have unit sales and 28.67 units with revenue of $200 in the  tier with â and Â and Ã."
    issues = find_report_language_issues(text)
    issue_strings = " ".join(issues)
    assert "unit sales" in issue_strings
    assert "units" in issue_strings
    assert "revenue" in issue_strings
    assert "$" in issue_strings
    assert " tier" in issue_strings
    assert "â" in issue_strings
    assert "Â" in issue_strings
    assert "Ã" in issue_strings


def test_rendered_story_html_does_not_contain_forbidden_terms() -> None:
    markdown_text = (
        "## Executive Takeaway\n\n"
        "Revenue dropped by $200 and unit sales fell by 28.67 units in 'l' prefix group tier.\n"
    )
    html = render_story_document(markdown_text, title="Test")
    assert "revenue" not in html.lower()
    assert "units" not in html.lower()
    assert "unit sales" not in html.lower()
    assert "tier" not in html.lower()
    assert "$" not in html
    assert "28.67 sales amount" in html.lower()
    assert "200 sales amount" in html.lower()
    assert "store group L" in html
