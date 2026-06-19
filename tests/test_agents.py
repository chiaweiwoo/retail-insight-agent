from __future__ import annotations

from dataclasses import dataclass

from rca import agents as agents_module
from rca.agents import run_coordinator, ANALYST_SPECS, plan_specialists
from rca.llm import LLMSettings


@dataclass
class FakeFunction:
    name: str
    arguments: str


@dataclass
class FakeToolCall:
    id: str
    function: FakeFunction


@dataclass
class FakeMessage:
    content: str | None = None
    tool_calls: list[FakeToolCall] | None = None


@dataclass
class FakeChoice:
    message: FakeMessage


@dataclass
class FakeResponse:
    choices: list[FakeChoice]


class SpecialistCompletions:
    last_messages = None

    def __init__(self, tool_name: str, actor_name: str) -> None:
        self.calls = 0
        self.tool_name = tool_name
        self.actor_name = actor_name

    def create(self, **kwargs):
        SpecialistCompletions.last_messages = kwargs.get("messages")
        self.calls += 1
        if self.calls == 1:
            return FakeResponse(
                choices=[
                    FakeChoice(
                        message=FakeMessage(
                            tool_calls=[
                                FakeToolCall(
                                    id=f"{self.actor_name}_call_1",
                                    function=FakeFunction(
                                        name=self.tool_name,
                                        arguments='{"store_alias":"h555","dt":"2024-05-16"}',
                                    ),
                                )
                            ]
                        )
                    )
                ]
            )
        return FakeResponse(
            choices=[
                FakeChoice(
                    message=FakeMessage(
                        content=f"## Scope\n{self.actor_name}\n\n## Findings\nDone.\n\n## Caveats\nNone."
                    )
                )
            ]
        )


class CoordinatorCompletions:
    last_messages = None

    def create(self, **kwargs):
        CoordinatorCompletions.last_messages = kwargs.get("messages")
        return FakeResponse(
            choices=[
                FakeChoice(
                    message=FakeMessage(
                        content="## Trigger\nDrop\n\n## Likely Drivers\nMixed.\n\n## Evidence\nCollected.\n\n## Caveats\nSome.\n\n## Suggested Next Checks\nMore."
                    )
                )
            ]
        )


class CriticCompletions:
    last_messages = None

    def create(self, **kwargs):
        CriticCompletions.last_messages = kwargs.get("messages")
        return FakeResponse(
            choices=[
                FakeChoice(
                    message=FakeMessage(
                        content="## Claim Audit\n- keep sales\n\n## Gaps\n- none\n\n## Calibration Note\n- be cautious"
                    )
                )
            ]
        )


class FinanceControllerCompletions:
    def create(self, **kwargs):
        return FakeResponse(
            choices=[
                FakeChoice(
                    message=FakeMessage(
                        content="## Materiality\nSmall.\n\n## Margin Risk\nUnknown.\n\n## One-off vs Structural\nUnclear."
                    )
                )
            ]
        )


class SltBriefCompletions:
    def create(self, **kwargs):
        return FakeResponse(
            choices=[
                FakeChoice(
                    message=FakeMessage(
                        content="## Decision Card - h555 2024-05-16\n- headline: Low confidence drop\n- confidence: low\n- materiality: small\n- pattern: first observed\n- action: none - monitor\n- escalate: no"
                    )
                )
            ]
        )


class FakeChat:
    def __init__(self, completions) -> None:
        self.completions = completions


class FakeClient:
    def __init__(self, completions) -> None:
        self.chat = FakeChat(completions)


def test_coordinator_runs_parallel_specialists_and_synthesizes(tmp_path) -> None:
    tool_by_actor = {
        "sales_analyst": "get_signal_evidence",
        "ops_analyst": "get_stockout_context",
        "commercial_analyst": "get_discount_context",
        "market_analyst": "get_calendar_weather_context",
        "research_analyst": "search_news",
    }

    def client_factory(actor_name: str):
        if actor_name == "coordinator_analyst":
            return FakeClient(CoordinatorCompletions())
        if actor_name == "critic":
            return FakeClient(CriticCompletions())
        if actor_name == "finance_controller":
            return FakeClient(FinanceControllerCompletions())
        if actor_name == "slt_brief":
            return FakeClient(SltBriefCompletions())
        tool = tool_by_actor.get(actor_name, "get_signal_evidence")
        return FakeClient(SpecialistCompletions(tool, actor_name))

    # Run with just the 4 core analysts (exclude research to avoid real web calls in tests)
    core_specs = [s for s in ANALYST_SPECS if s.name != "research_analyst"]
    result = run_coordinator(
        store_alias="h555",
        dt="2024-05-16",
        specialists=core_specs,
        settings=LLMSettings(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        ),
        client_factory=client_factory,
        output_dir=tmp_path / "scenario",
    )
    assert "## Trigger" in result.coordinator_report_markdown
    assert len(result.analyst_results) == 4
    assert "## Claim Audit" in result.critic_note_markdown
    assert "## Materiality" in result.controller_note_markdown
    assert "## Decision Card" in result.decision_card_markdown
    assert (tmp_path / "scenario" / "specialists" / "sales_analyst.md").exists()
    assert (tmp_path / "scenario" / "specialists" / "sales_analyst.html").exists()
    assert (tmp_path / "scenario" / "critique.md").exists()
    assert (tmp_path / "scenario" / "critique.html").exists()
    assert (tmp_path / "scenario" / "controller_note.md").exists()
    assert (tmp_path / "scenario" / "decision_card.md").exists()
    assert (tmp_path / "scenario" / "run_log.md").exists()
    assert (tmp_path / "scenario" / "run_log.jsonl").exists()
    assert (tmp_path / "scenario" / "run_trace.json").exists()
    assert (tmp_path / "scenario" / "report.html").exists()


def test_coordinator_quick_mode_uses_sales_analyst_only(tmp_path) -> None:
    """--quick mode: run_coordinator with only the sales_analyst specialist."""
    sales_spec = next(s for s in ANALYST_SPECS if s.name == "sales_analyst")

    def client_factory(actor_name: str):
        if actor_name == "coordinator_analyst":
            return FakeClient(CoordinatorCompletions())
        if actor_name == "critic":
            return FakeClient(CriticCompletions())
        if actor_name == "finance_controller":
            return FakeClient(FinanceControllerCompletions())
        if actor_name == "slt_brief":
            return FakeClient(SltBriefCompletions())
        return FakeClient(SpecialistCompletions("get_signal_evidence", actor_name))

    result = run_coordinator(
        store_alias="h555",
        dt="2024-05-16",
        specialists=[sales_spec],
        settings=LLMSettings(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        ),
        client_factory=client_factory,
    )
    assert "## Trigger" in result.coordinator_report_markdown
    assert len(result.analyst_results) == 1
    assert result.analyst_results[0].name == "sales_analyst"


def test_context_preamble_is_injected_into_specialist_and_coordinator_prompts(tmp_path) -> None:
    sales_spec = next(s for s in ANALYST_SPECS if s.name == "sales_analyst")

    def client_factory(actor_name: str):
        if actor_name == "coordinator_analyst":
            return FakeClient(CoordinatorCompletions())
        if actor_name == "critic":
            return FakeClient(CriticCompletions())
        if actor_name == "finance_controller":
            return FakeClient(FinanceControllerCompletions())
        if actor_name == "slt_brief":
            return FakeClient(SltBriefCompletions())
        return FakeClient(SpecialistCompletions("get_signal_evidence", actor_name))

    run_coordinator(
        store_alias="h555",
        dt="2024-05-16",
        specialists=[sales_spec],
        settings=LLMSettings(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        ),
        client_factory=client_factory,
        output_dir=tmp_path / "scenario",
    )
    specialist_system = SpecialistCompletions.last_messages[0]["content"]
    coordinator_system = CoordinatorCompletions.last_messages[0]["content"]
    assert "GROUNDING CONTEXT" in specialist_system
    assert "opaque anonymized identifiers" in specialist_system
    assert "GROUNDING CONTEXT" in coordinator_system
    assert "Critic note:" in CoordinatorCompletions.last_messages[1]["content"]


def test_plan_specialists_skips_ops_and_research_when_local_signal_is_empty(monkeypatch) -> None:
    monkeypatch.setattr(
        agents_module,
        "get_signal_evidence",
        lambda store_alias, dt: {
            "store_alias": store_alias,
            "dt": dt,
            "signal_label": "drop",
        },
    )
    monkeypatch.setattr(
        agents_module,
        "get_stockout_context",
        lambda store_alias, dt: {
            "avg_stockout_hours": 0.0,
            "stockout_product_rate": 0.0,
            "severe_stockout_product_rate": 0.0,
            "full_stockout_product_rate": 0.0,
            "hourly_stockout_rate_peak": 0.0,
        },
    )
    monkeypatch.setattr(
        agents_module,
        "get_discount_context",
        lambda store_alias, dt: {
            "discounted_product_rate": 0.0,
            "deep_discount_product_rate": 0.0,
        },
    )
    monkeypatch.setattr(
        agents_module,
        "get_activity_context",
        lambda store_alias, dt: {
            "activity_product_rate": 0.0,
            "activity_sales_share": 0.0,
        },
    )

    specialists = plan_specialists("h555", "2024-05-16")
    names = [spec.name for spec in specialists]

    assert names == ["sales_analyst", "market_analyst"]
