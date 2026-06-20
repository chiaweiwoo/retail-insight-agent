from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from openai import OpenAI

from rca.config import (
    get_llm_api_key,
    get_llm_base_url,
    get_llm_model,
    get_llm_thinking_enabled,
    get_model_deep,
    get_model_fast,
)


ClientFactory = Callable[[str], Any]

NODE_MODEL_MAP: dict[str, str] = {
    "planner": "deep",
    "statistician": "fast",
    "sales_agent": "fast",
    "inventory_agent": "fast",
    "pricing_agent": "fast",
    "promotions_agent": "fast",
    "calendar_weather_agent": "fast",
    "news_agent": "fast",
    "critic": "deep",
    "coordinator": "deep",
    "memory_distiller": "fast",
}


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


def make_routed_settings(base_settings: LLMSettings, node_name: str) -> LLMSettings:
    tier = NODE_MODEL_MAP.get(node_name, "deep")
    model = get_model_fast() if tier == "fast" else get_model_deep()
    return LLMSettings(
        api_key=base_settings.api_key,
        base_url=base_settings.base_url,
        model=model,
        thinking_enabled=base_settings.thinking_enabled,
    )


def build_chat_completion_kwargs(
    settings: LLMSettings,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": settings.model,
        "messages": messages,
        "temperature": 0.0,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
    if not settings.thinking_enabled and "deepseek" in settings.base_url:
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    return kwargs
