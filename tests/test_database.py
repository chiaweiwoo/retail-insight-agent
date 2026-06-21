from __future__ import annotations

import pandas as pd
import pytest

from rca.database import build_goals_df, build_signals_df


def _sales(sales: float, dt: str = "2024-04-29") -> pd.DataFrame:
    return pd.DataFrame([{"city_id": 0, "dt": dt, "total_sales": sales}])


def _goals(expected: float | None, method: str, dt: str = "2024-04-29") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "city_id": 0,
                "dt": dt,
                "expected_sales": expected,
                "goal_method": method,
                "recent_7d_avg_sales": expected,
                "same_weekday_4w_avg_sales": expected if method == "same_weekday_4w" else None,
            }
        ]
    )


def _calendar(dt: str = "2024-04-29", holiday: str = "normal_weekday") -> pd.DataFrame:
    return pd.DataFrame([{"city_id": 0, "dt": dt, "weekday": "monday", "holiday_name_inferred": holiday}])


def _signals(sales: float, expected: float | None, method: str, holiday: str = "normal_weekday") -> pd.Series:
    df = build_signals_df(_sales(sales), _goals(expected, method), _calendar(holiday=holiday), "v1")
    return df.iloc[0]


# ── Goals tests ───────────────────────────────────────────────────────────────


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


# ── Signal label tests ────────────────────────────────────────────────────────


def test_build_signals_labels_drop_and_preserves_build_version() -> None:
    row = _signals(80.0, 100.0, "recent_7d")
    assert row["signal_label"] == "drop"
    assert round(float(row["deviation_pct"]), 2) == -20.0
    assert row["build_version"] == "v1"


def test_build_signals_labels_lift() -> None:
    row = _signals(140.0, 100.0, "same_weekday_4w")
    assert row["signal_label"] == "lift"


def test_build_signals_labels_neutral() -> None:
    row = _signals(100.0, 100.0, "same_weekday_4w")
    assert row["signal_label"] == "neutral"


def test_build_signals_labels_insufficient_history_when_no_expected() -> None:
    row = _signals(100.0, None, "insufficient_history")
    assert row["signal_label"] == "insufficient_history"


# ── abs_deviation_pct ─────────────────────────────────────────────────────────


def test_abs_deviation_pct_matches_magnitude() -> None:
    row = _signals(80.0, 100.0, "recent_7d")
    assert round(float(row["abs_deviation_pct"]), 2) == 20.0


def test_abs_deviation_pct_is_null_when_no_expected() -> None:
    row = _signals(100.0, None, "insufficient_history")
    assert row["abs_deviation_pct"] is None or pd.isna(row["abs_deviation_pct"])


# ── signal_strength ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "sales,expected,want_strength",
    [
        # abs_deviation < 15  → weak  (signal is still drop since > 10% threshold)
        (88.0, 100.0, "weak"),     # -12%: drop, abs=12 < 15 → weak
        # 15 <= abs < 25      → moderate
        (80.0, 100.0, "moderate"), # -20%: drop, abs=20
        # 25 <= abs < 40      → strong
        (70.0, 100.0, "strong"),   # -30%: drop, abs=30
        # abs >= 40           → extreme
        (55.0, 100.0, "extreme"),  # -45%: drop, abs=45
        (50.0, 100.0, "extreme"),  # -50%: drop, abs=50
    ],
)
def test_signal_strength_values(sales: float, expected: float, want_strength: str) -> None:
    row = _signals(sales, expected, "same_weekday_4w")
    assert row["signal_strength"] == want_strength, f"sales={sales} expected={expected}"


def test_signal_strength_none_when_neutral() -> None:
    row = _signals(100.0, 100.0, "same_weekday_4w")
    assert row["signal_strength"] == "none"


def test_signal_strength_none_when_insufficient_history() -> None:
    row = _signals(100.0, None, "insufficient_history")
    assert row["signal_strength"] == "none"


# ── baseline_quality ──────────────────────────────────────────────────────────


def test_baseline_quality_strong_for_same_weekday() -> None:
    row = _signals(80.0, 100.0, "same_weekday_4w")
    assert row["baseline_quality"] == "strong"


def test_baseline_quality_usable_for_recent_7d() -> None:
    row = _signals(80.0, 100.0, "recent_7d")
    assert row["baseline_quality"] == "usable"


def test_baseline_quality_insufficient_when_no_history() -> None:
    row = _signals(100.0, None, "insufficient_history")
    assert row["baseline_quality"] == "insufficient"


# ── signal_reason ─────────────────────────────────────────────────────────────


def test_signal_reason_drop_contains_baseline_method() -> None:
    row = _signals(80.0, 100.0, "same_weekday_4w")
    assert "drop" in row["signal_reason"]
    assert "same_weekday_4w" in row["signal_reason"]


def test_signal_reason_insufficient_history() -> None:
    row = _signals(100.0, None, "insufficient_history")
    assert "insufficient" in row["signal_reason"]


# ── priority_score ────────────────────────────────────────────────────────────


def test_priority_score_zero_when_insufficient_history() -> None:
    row = _signals(100.0, None, "insufficient_history")
    assert row["priority_score"] == 0.0


def test_priority_score_higher_for_strong_signal() -> None:
    weak_row = _signals(92.0, 100.0, "same_weekday_4w")   # -8%, weak
    strong_row = _signals(55.0, 100.0, "same_weekday_4w")  # -45%, extreme
    assert float(strong_row["priority_score"]) > float(weak_row["priority_score"])


def test_priority_score_bonus_for_holiday() -> None:
    normal = _signals(80.0, 100.0, "same_weekday_4w", holiday="normal_weekday")
    holiday = _signals(80.0, 100.0, "same_weekday_4w", holiday="labor_day_period")
    assert float(holiday["priority_score"]) > float(normal["priority_score"])


# ── first_hypothesis_hints ────────────────────────────────────────────────────


def test_first_hypothesis_hints_is_json_compatible_dict() -> None:
    row = _signals(80.0, 100.0, "same_weekday_4w")
    hints = row["first_hypothesis_hints"]
    assert isinstance(hints, dict)
    assert "baseline" in hints
    assert "internal" in hints
    assert "external" in hints
    assert "cautions" in hints


def test_first_hypothesis_hints_all_lists() -> None:
    row = _signals(80.0, 100.0, "same_weekday_4w")
    hints = row["first_hypothesis_hints"]
    for key in ("baseline", "internal", "external", "cautions"):
        assert isinstance(hints[key], list), f"hints[{key!r}] is not a list"


def test_first_hypothesis_hints_cautions_include_normalized_sales() -> None:
    row = _signals(80.0, 100.0, "same_weekday_4w")
    cautions = row["first_hypothesis_hints"]["cautions"]
    assert any("normalized" in c for c in cautions)
