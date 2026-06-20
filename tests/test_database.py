from __future__ import annotations

import pandas as pd

from rca.database import build_goals_df, build_signals_df


def test_build_goals_prefers_same_weekday_then_recent_baseline() -> None:
    sales_df = pd.DataFrame(
        [
            {"city_id": 0, "dt": "2024-04-01", "total_sales": 100.0},
            {"city_id": 0, "dt": "2024-04-08", "total_sales": 110.0},
            {"city_id": 0, "dt": "2024-04-15", "total_sales": 120.0},
            {"city_id": 0, "dt": "2024-04-22", "total_sales": 130.0},
            {"city_id": 0, "dt": "2024-04-29", "total_sales": 80.0},
        ]
    )
    goals = build_goals_df(sales_df)
    latest = goals[goals["dt"] == "2024-04-29"].iloc[0]
    assert latest["goal_method"] == "same_weekday_4w"
    assert round(float(latest["expected_sales"]), 2) == 115.0


def test_build_signals_labels_drop_and_preserves_build_version() -> None:
    sales_df = pd.DataFrame([{"city_id": 0, "dt": "2024-04-29", "total_sales": 80.0}])
    goals_df = pd.DataFrame(
        [
            {
                "city_id": 0,
                "dt": "2024-04-29",
                "expected_sales": 100.0,
                "goal_method": "recent_7d",
                "recent_7d_avg_sales": 100.0,
                "same_weekday_4w_avg_sales": None,
            }
        ]
    )
    calendar_df = pd.DataFrame(
        [
            {
                "city_id": 0,
                "dt": "2024-04-29",
                "weekday": "monday",
                "holiday_name_inferred": "normal_weekday",
            }
        ]
    )
    signals = build_signals_df(sales_df, goals_df, calendar_df, "build_123")
    row = signals.iloc[0]
    assert row["signal_label"] == "drop"
    assert round(float(row["deviation_pct"]), 2) == -20.0
    assert row["build_version"] == "build_123"
