from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="store-era tests (OutcomeRecord fields, store_alias kwarg) — rewritten for city grain in Round E1")

from rca import agents as agents_module
from rca.agents import ANALYST_SPECS, run_coordinator
from rca.llm import LLMSettings
from rca.outcomes import OutcomeRecord, get_prior_rca, record_outcome
from rca.stubclient import stub_client_factory


def test_record_outcome_round_trip(tmp_path) -> None:
    db_path = tmp_path / "runs.duckdb"
    record_outcome(
        OutcomeRecord(
            run_name="test_run",
            store_alias="h555",
            dt="2024-05-16",
            signal_label="drop",
            top_driver="Possible stockout pressure",
            driver_class="inconclusive",
            confidence="low",
            escalated=False,
            brief_headline="Low confidence drop",
            decision_card_markdown="## Decision Card\n- headline: Low confidence drop\n- confidence: low\n- escalate: no",
        ),
        db_path=db_path,
    )

    summary = get_prior_rca("h555", db_path=db_path)
    assert summary["previous_trigger_count"] == 1
    assert summary["top_driver_counts"][0]["top_driver"] == "Possible stockout pressure"


def test_second_run_receives_prior_rca_pattern_in_stub_decision_card(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(agents_module, "LOG_DB_PATH", tmp_path / "runs.duckdb")
    sales_spec = next(spec for spec in ANALYST_SPECS if spec.name == "sales_analyst")
    settings = LLMSettings(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        thinking_enabled=False,
    )

    first = run_coordinator(
        store_alias="h555",
        dt="2024-05-16",
        specialists=[sales_spec],
        settings=settings,
        client_factory=stub_client_factory,
        output_dir=tmp_path / "first",
    )
    second = run_coordinator(
        store_alias="h555",
        dt="2024-05-16",
        specialists=[sales_spec],
        settings=settings,
        client_factory=stub_client_factory,
        output_dir=tmp_path / "second",
    )

    assert "first observed" in first.decision_card_markdown
    assert "recurring" in second.decision_card_markdown
