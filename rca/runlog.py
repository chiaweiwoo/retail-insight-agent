from __future__ import annotations

import json
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from rca.config import TABLE_EVENTS, current_timestamp_sgt_iso, make_supabase_schema_client


@dataclass
class RunLogger:
    run_id: str
    city_id: int
    dt: str
    events: list[dict[str, Any]] = field(default_factory=list)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def log(
        self,
        *,
        actor_type: str,
        actor_name: str,
        action: str,
        source: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            event = {
                "seq": len(self.events) + 1,
                "timestamp_sgt": current_timestamp_sgt_iso(),
                "run_id": self.run_id,
                "city_id": self.city_id,
                "dt": self.dt,
                "actor_type": actor_type,
                "actor_name": actor_name,
                "action": action,
                "source": source,
                "details": details or {},
            }
            self.events.append(event)
            return event

    def flush_to_supabase(self) -> None:
        if not self.events:
            return
        client = make_supabase_schema_client()
        try:
            client.table(TABLE_EVENTS).insert(
                [
                    {
                        "run_id": event["run_id"],
                        "city_id": event["city_id"],
                        "dt": event["dt"],
                        "seq": event["seq"],
                        "ts": event["timestamp_sgt"],
                        "actor_type": event["actor_type"],
                        "actor_name": event["actor_name"],
                        "action": event["action"],
                        "source": event["source"],
                        "details": event["details"],
                    }
                    for event in self.events
                ]
            ).execute()
        except Exception:
            return

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(event, ensure_ascii=False) for event in self.events) + "\n"
