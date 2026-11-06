"""Bronze layer (staging): CSV -> DuckDB, one table per file, all columns VARCHAR.

Values are stored exactly as they appear in the file so that nothing is lost
before validation.  Every row carries ingestion metadata:

    _source_file   absolute path of the CSV that produced the row
    _run_id        pipeline run identifier
    _ingested_at   ingestion timestamp

Bronze is fully replaced on every run (it always reflects the latest batch).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb

from .db import path_for_sql, quote_ident, scalar, sql_literal
from .logging_utils import get_logger

log = get_logger()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_csv(con: duckdb.DuckDBPyConnection, table: str, path: Path, run_id: str) -> int:
    sql = f"""
        CREATE OR REPLACE TABLE bronze.{quote_ident(table)} AS
        SELECT
            * EXCLUDE (filename),
            filename                  AS _source_file,
            {sql_literal(run_id)}     AS _run_id,
            now()::TIMESTAMP          AS _ingested_at
        FROM read_csv(
            {path_for_sql(path)},
            header = true,
            all_varchar = true,
            delim = ',',
            quote = '"',
            escape = '"',
            encoding = 'utf-8',
            filename = true,
            normalize_names = false
        )
    """
    con.execute(sql)
    return int(scalar(con, f"SELECT count(*) FROM bronze.{quote_ident(table)}"))


def load_bronze(con: duckdb.DuckDBPyConnection, files: dict[str, Path], run_id: str) -> dict[str, int]:
    con.execute("DROP SCHEMA IF EXISTS bronze CASCADE")
    con.execute("CREATE SCHEMA bronze")
    counts: dict[str, int] = {}
    for table, path in files.items():
        rows = ingest_csv(con, table, path, run_id)
        con.execute(
            "INSERT INTO audit.ingestion_log VALUES (?, ?, ?, ?, ?, ?, now())",
            [run_id, table, str(path.resolve()), path.stat().st_size, file_sha256(path), rows],
        )
        counts[table] = rows
        log.info("  bronze.%-34s %10d rows  <- %s", table, rows, path.name)
    return counts
