"""Deterministic stub LLM client for dry-runs and light tests."""
from __future__ import annotations

from typing import Any


STUB_RESPONSES: dict[str, str] = {
    "planner": '{"selected_agents":["statistician","sales_agent","inventory_agent","pricing_agent","promotions_agent","calendar_weather_agent"],"rationale":"Use all core agents for the learning harness.","news_query":"city {city} retail news {dt}","objective":"Validate the drop signal and identify key internal drivers.","target_gaps":[],"expected_evidence":["sales trend","inventory pressure","pricing data"]}',
    "statistician": "## Why It Matters\nSignal validity needs a descriptive baseline check.\n\n## Evidence\nRecent baseline and same-weekday checks both support the move.\n\n## Interpretation\nThe move is real in descriptive terms.\n\n## Caveats\nDescriptive evidence only, not causal proof.",
    "sales_agent": "## Why It Matters\nSales versus expected sales defines the decision surface.\n\n## Evidence\nCurrent sales are below the synthetic business goal.\n\n## Interpretation\nThe sales move is meaningful enough to investigate.\n\n## Caveats\nSynthetic goal, not a real corporate target.",
    "inventory_agent": "## Why It Matters\nAvailability can suppress realized sales.\n\n## Evidence\nStockout pressure is present in the stub path.\n\n## Interpretation\nInventory is a plausible contributing factor.\n\n## Caveats\nNo direct lost-sales estimate exists.",
    "pricing_agent": "## Why It Matters\nDiscounting can move sales while changing risk posture.\n\n## Evidence\nDiscount depth appears elevated in the stub path.\n\n## Interpretation\nPricing pressure may have influenced performance.\n\n## Caveats\nNo margin data is available.",
    "promotions_agent": "## Why It Matters\nThe activity flag may indicate a commercial push.\n\n## Evidence\nActivity is present, but unlabeled.\n\n## Interpretation\nPromotion-like behavior is plausible but not confirmed.\n\n## Caveats\nThe source flag is unlabeled.",
    "calendar_weather_agent": "## Why It Matters\nCalendar and weather can explain external demand shifts.\n\n## Evidence\nNo strong external calendar or weather surprise is visible in the stub path.\n\n## Interpretation\nThese factors are low-confidence explanations here.\n\n## Caveats\nHoliday naming is inferred.",
    "news_agent": "## Why It Matters\nExternal events can explain city-wide moves.\n\n## Evidence\nNo cached external event evidence in the stub path.\n\n## Interpretation\nExternal explanation remains inconclusive.\n\n## Caveats\nStub mode does not perform real search.",
    "critic": '{"continue_investigation":false,"confidence_ceiling":"medium","gaps":[],"recommended_agents":[],"recommended_tools":[],"stop_reason":"Sufficient evidence collected in stub mode."}',
    "coordinator": '{"headline":"Sales under plan with mixed internal evidence","confidence":"medium","situation":"City 0 recorded a real drop versus its synthetic business goal. Inventory pressure and promotion ambiguity are the strongest internal leads.","business_impact":"Normalized sales amount below baseline by a measurable amount. No margin or traffic data is available.","most_likely_explanation":"Inventory pressure is the most plausible factor. Stockout pressure is present and discount depth appears elevated. The activity flag is unlabeled so promotion contribution cannot be confirmed.","evidence_summary":["Stockout pressure is present in the stub path.","Discount depth appears elevated.","Activity flag is present but unlabeled."],"recommended_action":"Review stockout coverage first, then review unlabeled activity interpretation and promotion calendars.","alternatives":["External event explanation remains inconclusive.","Calendar or weather factors appear weak."],"owner_function":"Operations","urgency":"medium","expected_benefit":"Reduce recurrence risk in the next 7 days by addressing inventory gaps.","monitoring_plan":{"metrics_to_watch":["stockout_product_rate","total_sales","activity_sales_share"],"review_horizon":"7 days","escalation_trigger":"Drop repeats on next same-weekday cycle."},"unknowns":["Margin data is unavailable.","Promotion details behind the activity flag are unknown."],"caveats":["Synthetic goals are used for screening, not real corporate targets.","Activity flag meaning is unlabeled.","Holiday naming is inferred from date context."]}',
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
        rendered = template.replace("{city}", city).replace("{dt}", dt)
        return _StubResponse(rendered, kwargs.get("model", "stub-model"))


class _StubChat:
    def __init__(self, node_name: str) -> None:
        self.completions = _StubCompletions(node_name)


class StubClient:
    def __init__(self, node_name: str) -> None:
        self.chat = _StubChat(node_name)


def stub_client_factory(node_name: str) -> StubClient:
    return StubClient(node_name)
