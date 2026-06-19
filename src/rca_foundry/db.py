from __future__ import annotations

from pathlib import Path

import duckdb

from rca_foundry.config import DB_PATH, MIGRATION_PATH


def rebuild_database(
    db_path: Path = DB_PATH,
    migration_path: Path = MIGRATION_PATH,
) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    connection = duckdb.connect(str(db_path))
    migration_sql = migration_path.read_text(encoding="utf-8")
    connection.execute(migration_sql)
    return connection


def connect_database(db_path: Path = DB_PATH) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(db_path), read_only=True)
