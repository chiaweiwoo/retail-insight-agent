from __future__ import annotations

import pandas as pd
import pytest

from rca.signals import (
    build_pct_trigger_grid,
    build_sales_signal_frame,
    load_sales_history,
    recommend_primary_signal,
    summarize_pct_trigger_distribution,
    summarize_signal_distribution,
)


@pytest.mark.skip(reason="store-era: asserts 1350 rows (15 stores) and store_alias column — rewritten for city grain in Round E1")
def test_load_sales_history_shape() -> None:
    frame = load_sales_history()
    assert frame.shape[0] == 1350
    assert set(["store_alias", "dt", "total_sales", "weekday"]).issubset(frame.columns)


@pytest.mark.skip(reason="store-era: asserts 1350 rows (15 stores) — rewritten for city grain in Round E1")
def test_build_sales_signal_frame_adds_candidate_metrics() -> None:
    frame = load_sales_history()
    signals = build_sales_signal_frame(frame)
    assert signals.shape[0] == 1350
    assert "day_over_day_pct_change" in signals.columns
    assert "trailing_7d_pct_change" in signals.columns
    assert "same_weekday_4w_pct_change" in signals.columns
    assert signals["same_weekday_4w_pct_change"].notna().sum() > 0


@pytest.mark.skip(reason="store-era: uses store_alias groupby key — rewritten for city grain in Round E1")
def test_build_sales_signal_frame_on_toy_data() -> None:
    toy = pd.DataFrame(
        {
            "store_alias": ["h263"] * 8,
            "dt": pd.date_range("2024-03-28", periods=8, freq="D"),
            "total_sales": [100.0, 110.0, 90.0, 120.0, 130.0, 140.0, 150.0, 160.0],
            "weekday": [
                "thursday",
                "friday",
                "saturday",
                "sunday",
                "monday",
                "tuesday",
                "wednesday",
                "thursday",
            ],
            "is_weekend": [False, False, True, True, False, False, False, False],
            "holiday_name_inferred": ["normal_weekday"] * 8,
        }
    )
    signals = build_sales_signal_frame(toy)
    last_row = signals.iloc[-1]
    assert last_row["previous_day_sales"] == pytest.approx(150.0)
    assert last_row["day_over_day_abs_change"] == pytest.approx(10.0)
    assert last_row["day_over_day_pct_change"] == pytest.approx((10.0 / 150.0) * 100.0)
    assert last_row["trailing_7d_avg_sales"] == pytest.approx(120.0)


def test_summarize_signal_distribution_outputs_tables() -> None:
    signals = build_sales_signal_frame(load_sales_history())
    summary = summarize_signal_distribution(signals)
    assert set(summary.keys()) == {"distribution", "thresholds", "city_stability"}
    assert not summary["distribution"].empty
    assert not summary["thresholds"].empty
    assert not summary["city_stability"].empty


def test_recommend_primary_signal_is_supported_metric() -> None:
    signals = build_sales_signal_frame(load_sales_history())
    summary = summarize_signal_distribution(signals)
    recommended = recommend_primary_signal(summary)
    assert recommended in {
        "day_over_day_pct_change",
        "trailing_7d_pct_change",
        "same_weekday_4w_pct_change",
    }


@pytest.mark.skip(reason="store-era: asserts per_store==75 (15 stores×5 thresholds) — rewritten for city grain in Round E1")
def test_summarize_pct_trigger_distribution_outputs_expected_shapes() -> None:
    signals = build_sales_signal_frame(load_sales_history())
    summary = summarize_pct_trigger_distribution(
        signals,
        metric="trailing_7d_pct_change",
    )
    assert set(summary.keys()) == {"overall", "per_store", "per_date"}
    assert len(summary["overall"]) == 5
    assert len(summary["per_store"]) == 75
    assert not summary["per_date"].empty


@pytest.mark.skip(reason="store-era: asserts grid.shape[0]==15 (15 stores) — rewritten for city grain in Round E1")
def test_build_pct_trigger_grid_shape() -> None:
    signals = build_sales_signal_frame(load_sales_history())
    grid = build_pct_trigger_grid(
        signals,
        metric="trailing_7d_pct_change",
        pct_threshold=20,
    )
    assert grid.shape[0] == 15
    assert grid.shape[1] == 87
    assert set(grid.to_numpy().ravel()).issubset({".", "D", "L"})
