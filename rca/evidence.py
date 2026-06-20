from __future__ import annotations

from typing import Any

from rca.tools import (
    get_calendar_weather_context,
    get_inventory_context,
    get_intraday_profile,
    get_pricing_context,
    get_promotions_context,
    get_sales_context,
    get_signal_evidence,
)


def get_city_day_evidence(city_id: int, dt: str) -> dict[str, Any]:
    return {
        "signal": get_signal_evidence(city_id, dt),
        "sales": get_sales_context(city_id, dt),
        "inventory": get_inventory_context(city_id, dt),
        "pricing": get_pricing_context(city_id, dt),
        "promotions": get_promotions_context(city_id, dt),
        "calendar_weather": get_calendar_weather_context(city_id, dt),
        "intraday": get_intraday_profile(city_id, dt),
    }
