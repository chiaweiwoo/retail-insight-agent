from __future__ import annotations

from dataclasses import dataclass

from rca_foundry.agent import run_rca_agent
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


class FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return FakeResponse(
                choices=[
                    FakeChoice(
                        message=FakeMessage(
                            tool_calls=[
                                FakeToolCall(
                                    id="call_1",
                                    function=FakeFunction(
                                        name="get_signal_evidence",
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
                        content="## Trigger\nDrop\n\n## Likely Drivers\nMixed.\n"
                    )
                )
            ]
        )


class FakeChat:
    def __init__(self) -> None:
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self) -> None:
        self.chat = FakeChat()


def test_run_rca_agent_executes_tool_then_returns_report() -> None:
    client = FakeClient()
    result = run_rca_agent(
        store_alias="h555",
        dt="2024-05-16",
        client=client,
        settings=LLMSettings(
            api_key="test-key",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            thinking_enabled=False,
        ),
    )
    assert "## Trigger" in result.report_markdown
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "get_signal_evidence"
