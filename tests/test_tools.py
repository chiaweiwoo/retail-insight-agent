from __future__ import annotations

from rca.tools import execute_tool, get_tool_schemas


def test_tool_schemas_include_signal_and_news_tools() -> None:
    names = {tool["function"]["name"] for tool in get_tool_schemas()}
    assert "get_signal_evidence" in names
    assert "search_external_events" in names


def test_execute_tool_returns_error_for_unknown_tool() -> None:
    result = execute_tool("does_not_exist", {})
    assert "error" in result
