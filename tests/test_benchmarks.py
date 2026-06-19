from __future__ import annotations

from rca.bench import SCENARIOS
from rca.config import current_timestamp_sgt_label


def test_bench_exposes_six_fixed_scenarios() -> None:
    assert len(SCENARIOS) == 6
    scenario_ids = {scenario.scenario_id for scenario in SCENARIOS}
    assert "drop_high_h555_2024-05-16" in scenario_ids
    assert "lift_low_l185_2024-04-13" in scenario_ids


def test_timestamp_label_uses_sgt_suffix() -> None:
    timestamp_label = current_timestamp_sgt_label()
    assert timestamp_label.endswith("_SGT")
    assert len(timestamp_label) == len("20260619T222335_SGT")
