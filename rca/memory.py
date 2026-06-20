from __future__ import annotations

import hashlib
import json
from typing import Any

from rca.config import (
    TABLE_EVIDENCE_CACHE,
    TABLE_EXTERNAL_EVENTS,
    TABLE_MEMORY,
    make_supabase_schema_client,
)
from rca.database import get_current_build_version


def _stable_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _cache_key(tool_name: str, params: dict[str, Any], build_version: str | None) -> str:
    payload = {"tool_name": tool_name, "params": params, "build_version": build_version or ""}
    return hashlib.sha256(_stable_json(payload).encode("utf-8")).hexdigest()


def get_memory_notes(city_id: int, limit: int = 5) -> list[dict[str, Any]]:
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_MEMORY)
        .select("memory_type,topic,content,created_at")
        .eq("city_id", city_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data or []


def write_memory(
    *,
    city_id: int,
    dt: str,
    run_id: str,
    memory_type: str,
    topic: str,
    content: str,
    signal_label: str,
) -> None:
    client = make_supabase_schema_client()
    try:
        client.table(TABLE_MEMORY).insert(
            {
                "city_id": city_id,
                "dt": dt,
                "run_id": run_id,
                "memory_type": memory_type,
                "topic": topic,
                "content": content,
                "signal_label": signal_label,
            }
        ).execute()
    except Exception:
        return


def get_cached_evidence(tool_name: str, params: dict[str, Any]) -> dict[str, Any] | None:
    build_version = get_current_build_version()
    cache_key = _cache_key(tool_name, params, build_version)
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_EVIDENCE_CACHE)
        .select("result_json")
        .eq("cache_key", cache_key)
        .limit(1)
        .execute()
    )
    rows = result.data or []
    if not rows:
        return None
    return rows[0].get("result_json")


def put_cached_evidence(tool_name: str, params: dict[str, Any], result_json: dict[str, Any]) -> None:
    build_version = get_current_build_version()
    cache_key = _cache_key(tool_name, params, build_version)
    client = make_supabase_schema_client()
    try:
        client.table(TABLE_EVIDENCE_CACHE).upsert(
            {
                "cache_key": cache_key,
                "build_version": build_version,
                "city_id": params.get("city_id"),
                "dt": params.get("dt"),
                "tool_name": tool_name,
                "params_json": params,
                "result_json": result_json,
            },
            on_conflict="cache_key",
        ).execute()
    except Exception:
        return


def get_cached_external_events(city_id: int, dt: str, query: str) -> list[dict[str, Any]]:
    client = make_supabase_schema_client()
    result = (
        client.table(TABLE_EXTERNAL_EVENTS)
        .select("source,title,url,snippet,published_at,result_json")
        .eq("city_id", city_id)
        .eq("dt", dt)
        .eq("query", query)
        .order("id")
        .execute()
    )
    return result.data or []


def cache_external_events(city_id: int, dt: str, query: str, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    client = make_supabase_schema_client()
    records = []
    for row in rows:
        records.append(
            {
                "city_id": city_id,
                "dt": dt,
                "query": query,
                "source": row.get("source", "web"),
                "title": row.get("title", ""),
                "url": row.get("url", ""),
                "snippet": row.get("snippet", ""),
                "published_at": row.get("published_at"),
                "result_json": row,
            }
        )
    try:
        client.table(TABLE_EXTERNAL_EVENTS).insert(records).execute()
    except Exception:
        return
