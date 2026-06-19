from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from rca_foundry.config import (
    get_llm_api_key,
    get_llm_base_url,
    get_llm_model,
    get_llm_thinking_enabled,
)


@dataclass(frozen=True)
class LLMSettings:
    api_key: str
    base_url: str
    model: str
    thinking_enabled: bool


def load_llm_settings() -> LLMSettings:
    return LLMSettings(
        api_key=get_llm_api_key(),
        base_url=get_llm_base_url(),
        model=get_llm_model(),
        thinking_enabled=get_llm_thinking_enabled(),
    )


def build_openai_compatible_client(settings: LLMSettings | None = None) -> OpenAI:
    settings = settings or load_llm_settings()
    return OpenAI(api_key=settings.api_key, base_url=settings.base_url)


def build_chat_completion_kwargs(
    settings: LLMSettings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    if not settings.thinking_enabled and "deepseek" in settings.base_url:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    return kwargs
