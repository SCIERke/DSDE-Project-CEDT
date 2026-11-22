import json
import types
import uuid
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from typing import Any, Union, get_args, get_origin

import duckdb

from core import config  # read at call time so tests can point it at a temp lake

_SQL = {str: "VARCHAR", bool: "BOOLEAN", int: "BIGINT", float: "DOUBLE", datetime: "TIMESTAMP", list: "VARCHAR[]", dict: "JSON"}


def get_conn() -> duckdb.DuckDBPyConnection:
    Path(config.LAKE_META).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect()
    conn.execute("INSTALL ducklake; LOAD ducklake")
    conn.execute(f"ATTACH 'ducklake:{config.LAKE_META}' AS lake (DATA_PATH '{config.LAKE_DATA}')")
    conn.execute("USE lake")
    return conn

def ensure_raw_table(conn) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    conn.execute("CREATE TABLE IF NOT EXISTS bronze.raw_data "
                 "(id VARCHAR NOT NULL, source VARCHAR NOT NULL, payload JSON NOT NULL, fetched_at TIMESTAMP NOT NULL)")


def save_raw(name: str, data: Any) -> None:
    with get_conn() as conn:
        ensure_raw_table(conn)
        conn.execute("INSERT INTO bronze.raw_data VALUES (?, ?, ?, ?)",
                     [str(uuid.uuid4()), name, json.dumps(data), datetime.now()])


def bronze_sources(conn) -> list[str]:
    ensure_raw_table(conn)
    return [r[0] for r in conn.execute("SELECT DISTINCT source FROM bronze.raw_data ORDER BY source").fetchall()]


def latest_raw(conn, source: str) -> tuple[str, Any]:
    bronze_id, payload = conn.execute(
        "SELECT id, payload FROM bronze.raw_data WHERE source = ? ORDER BY fetched_at DESC LIMIT 1", [source]).fetchone()
    return bronze_id, json.loads(payload)


# ---- silver -----------------------------------------------------------------

def sql_type(t) -> str:
    if get_origin(t) in (Union, types.UnionType):  # `X | None` -> X
        t = next(a for a in get_args(t) if a is not type(None))
    return _SQL[get_origin(t) or t]


def ensure_table(conn, table: str, cls) -> None:
    cols = ", ".join(f'"{f.name}" {sql_type(f.type)}' for f in fields(cls))
    conn.execute("CREATE SCHEMA IF NOT EXISTS silver")
    conn.execute(f"CREATE TABLE IF NOT EXISTS silver.{table} (bronze_id VARCHAR NOT NULL, source VARCHAR NOT NULL, {cols})")


def append_rows(conn, table: str, cls, objs: list, source: str, bronze_id: str) -> None:
    ensure_table(conn, table, cls)
    conn.execute(f"DELETE FROM silver.{table} WHERE bronze_id = ?", [bronze_id])
    rows = [{"bronze_id": bronze_id, "source": source,
             **{f.name: (json.dumps(v) if isinstance(v, dict) else v) for f in fields(cls) for v in [getattr(o, f.name)]}}
            for o in objs]
    if rows:
        conn.execute(f"INSERT INTO silver.{table} BY NAME SELECT s.* FROM (SELECT unnest(?) AS s)", [rows])


def append_rejects(conn, rejected: list[tuple[dict, str]], source: str, bronze_id: str) -> None:
    conn.execute("CREATE SCHEMA IF NOT EXISTS silver")
    conn.execute("CREATE TABLE IF NOT EXISTS silver.rejects "
                 "(bronze_id VARCHAR NOT NULL, source VARCHAR NOT NULL, reason VARCHAR NOT NULL, row JSON NOT NULL)")
    conn.execute("DELETE FROM silver.rejects WHERE bronze_id = ?", [bronze_id])
    rows = [{"bronze_id": bronze_id, "source": source, "reason": why, "row": json.dumps(row, default=str)}
            for row, why in rejected]
    if rows:
        conn.execute("INSERT INTO silver.rejects BY NAME SELECT s.* FROM (SELECT unnest(?) AS s)", [rows])
