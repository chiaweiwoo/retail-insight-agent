from __future__ import annotations

from rca.runlog import RunLogger


def test_run_logger_captures_and_renders_events() -> None:
    logger = RunLogger(run_name="demo_run")
    logger.log(
        actor_type="agent",
        actor_name="sales_analyst",
        action="started",
        subject="h555:2024-05-16",
        source="system",
        details={"focus": "signal"},
    )
    logger.log(
        actor_type="tool",
        actor_name="get_signal_evidence",
        action="completed",
        subject="h555:2024-05-16",
        source="tool",
        details={"called_by": "sales_analyst"},
    )
    jsonl = logger.to_jsonl()
    markdown = logger.to_markdown()
    assert '"actor_name": "sales_analyst"' in jsonl
    assert "| 1 |" in markdown
    assert "get_signal_evidence" in markdown
