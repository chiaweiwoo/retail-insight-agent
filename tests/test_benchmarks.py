from __future__ import annotations

from pathlib import Path

from runpy import run_path


def test_benchmark_script_exposes_six_fixed_scenarios() -> None:
    script_globals = run_path(
        str(Path(__file__).resolve().parents[1] / "scripts" / "run_rca_benchmarks.py"),
        run_name="benchmark_test_module",
    )
    scenarios = script_globals["SCENARIOS"]
    assert len(scenarios) == 6
    scenario_ids = {scenario.scenario_id for scenario in scenarios}
    assert "drop_high_h555_2024-05-16" in scenario_ids
    assert "lift_low_l185_2024-04-13" in scenario_ids
