from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

import duckdb

from rca.config import current_timestamp_sgt_iso


@dataclass
class RunLogger:
    run_name: str
    events: list[dict[str, Any]] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def log(
        self,
        *,
        actor_type: str,
        actor_name: str,
        action: str,
        subject: str,
        source: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            event = {
                "seq": len(self.events) + 1,
                "timestamp_sgt": current_timestamp_sgt_iso(),
                "run_name": self.run_name,
                "actor_type": actor_type,
                "actor_name": actor_name,
                "action": action,
                "subject": subject,
                "source": source,
                "details": details or {},
            }
            self.events.append(event)
            return event

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(event, ensure_ascii=False) for event in self.events) + "\n"

    def to_markdown(self) -> str:
        lines = [
            "# Event Log",
            "",
            "| seq | timestamp_sgt | actor_type | actor_name | action | subject | source | details |",
            "| ---: | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for event in self.events:
            details_text = json.dumps(event["details"], ensure_ascii=False, sort_keys=True)
            details_text = details_text.replace("|", "\\|")
            line_values = {
                "seq": event["seq"],
                "timestamp_sgt": event["timestamp_sgt"],
                "actor_type": event["actor_type"],
                "actor_name": event["actor_name"],
                "action": event["action"],
                "subject": event["subject"],
                "source": event["source"],
                "details_text": details_text,
            }
            lines.append(
                "| {seq} | {timestamp_sgt} | {actor_type} | {actor_name} | {action} | {subject} | {source} | `{details_text}` |".format(
                    **line_values,
                )
            )
        lines.append("")
        return "\n".join(lines)

    def write_to_db(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect(str(db_path))
        con.execute("""
            CREATE TABLE IF NOT EXISTS run_log_event (
                seq        INTEGER NOT NULL,
                timestamp_sgt TEXT NOT NULL,
                run_name   TEXT NOT NULL,
                actor_type TEXT NOT NULL,
                actor_name TEXT NOT NULL,
                action     TEXT NOT NULL,
                subject    TEXT NOT NULL,
                source     TEXT NOT NULL,
                details_json TEXT NOT NULL
            )
        """)
        rows = [
            (
                event["seq"],
                event["timestamp_sgt"],
                event["run_name"],
                event["actor_type"],
                event["actor_name"],
                event["action"],
                event["subject"],
                event["source"],
                json.dumps(event["details"], ensure_ascii=False),
            )
            for event in self.events
        ]
        con.executemany("INSERT INTO run_log_event VALUES (?,?,?,?,?,?,?,?,?)", rows)
        con.close()
