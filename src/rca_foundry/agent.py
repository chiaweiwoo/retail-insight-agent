from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from rca_foundry.config import DEFAULT_LLM_MAX_TOOL_ROUNDS
from rca_foundry.llm import (
    LLMSettings,
    build_chat_completion_kwargs,
    build_openai_compatible_client,
    load_llm_settings,
)
from rca_foundry.rca_tools import execute_tool, get_tool_schemas


SYSTEM_PROMPT = """You are a retail root cause analysis analyst.

Your job is to analyze one store on one date using the available tools.

Rules:
- Use tools before concluding.
- Prefer to call each tool at most once unless you have a specific reason to revisit it.
- Ground every claim in tool evidence.
- Focus on the likely causes behind a sales drop or lift.
- Be explicit when evidence is weak or mixed.
- Separate observed evidence from causal inference.
- Use cautious language such as "likely", "suggests", or "is consistent with" unless the evidence is overwhelming.
- If a pattern could reflect either cause or consequence, say so plainly.
- Do not invent external facts.
- Use plain ASCII only. Do not use emojis, decorative symbols, or smart punctuation.

Return a concise markdown report with these sections:
1. Trigger
2. Likely Drivers
3. Evidence
4. Caveats
5. Suggested Next Checks
"""


@dataclass
class AgentRunResult:
    store_alias: str
    dt: str
    report_markdown: str
    tool_calls: list[dict[str, Any]]


def _tool_result_message(tool_call_id: str, name: str, result: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "name": name,
        "content": json.dumps(result),
    }


def run_rca_agent(
    store_alias: str,
    dt: str,
    client: Any | None = None,
    settings: LLMSettings | None = None,
    max_tool_rounds: int = DEFAULT_LLM_MAX_TOOL_ROUNDS,
) -> AgentRunResult:
    settings = settings or load_llm_settings()
    client = client or build_openai_compatible_client(settings)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Analyze store {store_alias} on {dt}. "
                "Figure out whether the signal is a drop or lift, inspect likely drivers, "
                "and produce an evidence-backed RCA note."
            ),
        },
    ]

    tool_schemas = get_tool_schemas()
    executed_tool_calls: list[dict[str, Any]] = []

    for _ in range(max_tool_rounds):
        response = client.chat.completions.create(
            **build_chat_completion_kwargs(settings, messages, tool_schemas)
        )
        message = response.choices[0].message

        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            content = getattr(message, "content", None) or ""
            return AgentRunResult(
                store_alias=store_alias,
                dt=dt,
                report_markdown=content,
                tool_calls=executed_tool_calls,
            )

        assistant_message: dict[str, Any] = {
            "role": "assistant",
            "content": getattr(message, "content", None) or "",
            "tool_calls": [],
        }

        for tool_call in tool_calls:
            raw_arguments = tool_call.function.arguments or "{}"
            arguments = json.loads(raw_arguments)
            result = execute_tool(tool_call.function.name, arguments)
            executed_tool_calls.append(
                {
                    "id": tool_call.id,
                    "name": tool_call.function.name,
                    "arguments": arguments,
                    "result": result,
                }
            )
            assistant_message["tool_calls"].append(
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": raw_arguments,
                    },
                }
            )
        messages.append(assistant_message)
        for tool_call in executed_tool_calls[-len(tool_calls) :]:
            messages.append(
                _tool_result_message(
                    tool_call["id"],
                    tool_call["name"],
                    tool_call["result"],
                )
            )

    raise RuntimeError(
        f"Agent exceeded the maximum tool rounds ({max_tool_rounds}) without finishing."
    )
