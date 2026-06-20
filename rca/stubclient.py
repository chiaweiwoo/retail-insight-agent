"""Deterministic stub LLM client for dry-runs and light tests."""
from __future__ import annotations

from typing import Any


STUB_RESPONSES: dict[str, str] = {
    "planner": '{"selected_agents":["statistician","sales_agent","inventory_agent","pricing_agent","promotions_agent","calendar_weather_agent","news_agent"],"rationale":"Use all core agents for the learning harness.","news_query":"city {city} retail news {dt}"}',
    "statistician": "## Why It Matters\nSignal validity needs a descriptive baseline check.\n\n## Evidence\nRecent baseline and same-weekday checks both support the move.\n\n## Interpretation\nThe move is real in descriptive terms.\n\n## Caveats\nDescriptive evidence only, not causal proof.",
    "sales_agent": "## Why It Matters\nSales versus expected sales defines the decision surface.\n\n## Evidence\nCurrent sales are below the synthetic business goal.\n\n## Interpretation\nThe sales move is meaningful enough to investigate.\n\n## Caveats\nSynthetic goal, not a real corporate target.",
    "inventory_agent": "## Why It Matters\nAvailability can suppress realized sales.\n\n## Evidence\nStockout pressure is present in the stub path.\n\n## Interpretation\nInventory is a plausible contributing factor.\n\n## Caveats\nNo direct lost-sales estimate exists.",
    "pricing_agent": "## Why It Matters\nDiscounting can move sales while changing risk posture.\n\n## Evidence\nDiscount depth appears elevated in the stub path.\n\n## Interpretation\nPricing pressure may have influenced performance.\n\n## Caveats\nNo margin data is available.",
    "promotions_agent": "## Why It Matters\nThe activity flag may indicate a commercial push.\n\n## Evidence\nActivity is present, but unlabeled.\n\n## Interpretation\nPromotion-like behavior is plausible but not confirmed.\n\n## Caveats\nThe source flag is unlabeled.",
    "calendar_weather_agent": "## Why It Matters\nCalendar and weather can explain external demand shifts.\n\n## Evidence\nNo strong external calendar or weather surprise is visible in the stub path.\n\n## Interpretation\nThese factors are low-confidence explanations here.\n\n## Caveats\nHoliday naming is inferred.",
    "news_agent": "## Why It Matters\nExternal events can explain city-wide moves.\n\n## Evidence\nNo cached external event evidence in the stub path.\n\n## Interpretation\nExternal explanation remains inconclusive.\n\n## Caveats\nStub mode does not perform real search.",
    "critic": "## Claim Audit\nMost claims are grounded, but causality remains soft.\n\n## Gaps\nNo direct margin, traffic, or competitor data.\n\n## Calibration\nUse medium confidence at most.\n\n## Follow Up\n- follow_up_needed: no",
    "coordinator": "# Decision Card\n- headline: Sales under plan with mixed internal evidence\n- confidence: medium\n- signal: drop\n\n## RCA\nThe city/date shows a real drop versus its synthetic business goal. Inventory pressure and promotion ambiguity are the strongest internal leads, while external evidence remains thin.\n\n## Internal Factors\nInventory pressure is plausible. Discount and activity signals exist but cannot be interpreted too strongly.\n\n## External Factors\nNo strong external event is confirmed in the stub path.\n\n## Prediction\nIf the pattern repeats on the next same-weekday cycle, this is more likely an operational recurring issue than a one-off.\n\n## Prescription\nReview stockout coverage first, then review unlabeled activity interpretation and promotion calendars.\n\n## Caveats\nSynthetic goals, unlabeled activity, inferred holidays, and missing margin data limit confidence.",
    "memory_distiller": "## Lessons\n- Re-check stockout evidence before escalating.\n- Treat activity_flag as unlabeled.\n- Synthetic goals are useful for screening, not proof.",
}


class _StubMessage:
    def __init__(self, content: str) -> None:
        self.content = content
        self.tool_calls = None


class _StubChoice:
    def __init__(self, content: str) -> None:
        self.message = _StubMessage(content)


class _StubUsage:
    prompt_tokens = 100
    completion_tokens = 50
    total_tokens = 150


class _StubResponse:
    def __init__(self, content: str, model: str) -> None:
        self.choices = [_StubChoice(content)]
        self.usage = _StubUsage()
        self.model = model


class _StubCompletions:
    def __init__(self, node_name: str) -> None:
        self.node_name = node_name

    def create(self, **kwargs: Any) -> _StubResponse:
        messages = kwargs.get("messages") or []
        city = "0"
        dt = "2024-05-16"
        for message in reversed(messages):
            content = message.get("content")
            if isinstance(content, str) and "city" in content and "2024-" in content:
                city = "0"
                dt = "2024-05-16"
                break
        template = STUB_RESPONSES.get(self.node_name, STUB_RESPONSES["sales_agent"])
        return _StubResponse(template.format(city=city, dt=dt), kwargs.get("model", "stub-model"))


class _StubChat:
    def __init__(self, node_name: str) -> None:
        self.completions = _StubCompletions(node_name)


class StubClient:
    def __init__(self, node_name: str) -> None:
        self.chat = _StubChat(node_name)


def stub_client_factory(node_name: str) -> StubClient:
    return StubClient(node_name)
