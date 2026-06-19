from __future__ import annotations

from dataclasses import dataclass

from rca_foundry.multi_agent import run_manager_analyst_pipeline
from rca_foundry.llm import LLMSettings


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
    def __init__(self, tool_name: str, actor_name: str) -> None:
        self.calls = 0
        self.tool_name = tool_name
        self.actor_name = actor_name

    def create(self, **kwargs):
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


class ManagerCompletions:
    def create(self, **kwargs):
        return FakeResponse(
            choices=[
                FakeChoice(
                    message=FakeMessage(
                        content="## Trigger\nDrop\n\n## Likely Drivers\nMixed.\n\n## Evidence\nCollected.\n\n## Caveats\nSome.\n\n## Suggested Next Checks\nMore."
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


def test_manager_pipeline_runs_parallel_specialists_and_manager(tmp_path) -> None:
    tool_by_actor = {
        "signal_analyst": "get_signal_evidence",
        "inventory_analyst": "get_stockout_context",
        "pricing_activity_analyst": "get_discount_context",
        "context_analyst": "get_calendar_weather_context",
    }

    def client_factory(actor_name: str):
        if actor_name == "manager_analyst":
            return FakeClient(ManagerCompletions())
        return FakeClient(SpecialistCompletions(tool_by_actor[actor_name], actor_name))

    result = run_manager_analyst_pipeline(
        store_alias="h555",
        dt="2024-05-16",
        settings=LLMSettings(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        ),
        client_factory=client_factory,
        output_dir=tmp_path / "scenario",
    )
    assert "## Trigger" in result.manager_report_markdown
    assert len(result.analyst_results) == 4
    assert (tmp_path / "scenario" / "logs" / "event_log.jsonl").exists()
    assert (tmp_path / "scenario" / "specialists" / "signal_analyst.md").exists()
