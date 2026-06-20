from __future__ import annotations

from rca.runlog import RunLogger


def test_run_logger_captures_jsonl() -> None:
    logger = RunLogger(run_id="demo", city_id=0, dt="2024-05-16")
    logger.log(actor_type="agent", actor_name="planner", action="started", source="system", details={"focus": "plan"})
    logger.log(actor_type="tool", actor_name="get_signal_evidence", action="completed", source="planner", details={"city_id": 0})
    jsonl = logger.to_jsonl()
    assert '"actor_name": "planner"' in jsonl
    assert '"action": "completed"' in jsonl
