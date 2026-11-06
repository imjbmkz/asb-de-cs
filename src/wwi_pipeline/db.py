"""DuckDB connection management, SQL-file execution and audit helpers."""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import duckdb

from .config import SQL_DIR, Settings
from .logging_utils import get_logger

log = get_logger()


def connect(settings: Settings) -> duckdb.DuckDBPyConnection:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(settings.db_path))
    if settings.threads:
        con.execute(f"SET threads = {int(settings.threads)}")
    if settings.memory_limit:
        con.execute(f"SET memory_limit = '{settings.memory_limit}'")
    con.execute("SET preserve_insertion_order = false")
    return con


def render_sql(sql: str, params: dict[str, Any] | None = None) -> str:
    """Substitute ``{{name}}`` placeholders (identifiers / literals controlled by the pipeline)."""
    params = params or {}

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in params:
            raise KeyError(f"Missing SQL template parameter: {key}")
        return str(params[key])

    return re.sub(r"\{\{\s*(\w+)\s*\}\}", _sub, sql)


def read_sql(relative_path: str, params: dict[str, Any] | None = None) -> str:
    return render_sql((SQL_DIR / relative_path).read_text(encoding="utf-8"), params)


def run_sql_file(con: duckdb.DuckDBPyConnection, relative_path: str, params: dict[str, Any] | None = None) -> None:
    log.info("  executing sql/%s", relative_path)
    con.execute(read_sql(relative_path, params))


def scalar(con: duckdb.DuckDBPyConnection, sql: str, params: list[Any] | None = None) -> Any:
    row = con.execute(sql, params or []).fetchone()
    return None if row is None else row[0]


@contextmanager
def transaction(con: duckdb.DuckDBPyConnection) -> Iterator[duckdb.DuckDBPyConnection]:
    con.execute("BEGIN TRANSACTION")
    try:
        yield con
    except Exception:
        con.execute("ROLLBACK")
        raise
    else:
        con.execute("COMMIT")


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


# --------------------------------------------------------------------------- audit
def ensure_audit_schema(con: duckdb.DuckDBPyConnection) -> None:
    run_sql_file(con, "audit_ddl.sql")


def log_step(
    con: duckdb.DuckDBPyConnection,
    run_id: str,
    step: str,
    status: str,
    started_at: Any,
    finished_at: Any,
    message: str | None = None,
) -> None:
    con.execute(
        "INSERT INTO audit.step_log VALUES (?, ?, ?, ?, ?, date_diff('millisecond', ?::TIMESTAMP, ?::TIMESTAMP) / 1000.0, ?)",
        [run_id, step, status, started_at, finished_at, started_at, finished_at, message],
    )


def log_metric(con: duckdb.DuckDBPyConnection, run_id: str, step: str, name: str, value: Any, detail: Any = None) -> None:
    con.execute(
        "INSERT INTO audit.run_metrics VALUES (?, ?, ?, ?, ?, now())",
        [run_id, step, name, None if value is None else float(value), None if detail is None else json.dumps(detail, default=str)],
    )


def table_exists(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> bool:
    return bool(
        scalar(
            con,
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?",
            [schema, table],
        )
    )


def row_count(con: duckdb.DuckDBPyConnection, schema: str, table: str) -> int:
    return int(scalar(con, f"SELECT count(*) FROM {quote_ident(schema)}.{quote_ident(table)}"))


def path_for_sql(path: Path) -> str:
    return sql_literal(path.resolve().as_posix())
