"""Evidence generation: run summaries and business-query results as Markdown."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import duckdb

from .config import SQL_DIR
from .db import read_sql


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}"
    if isinstance(value, Decimal):
        return f"{value:,.2f}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def to_markdown(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None, limit: int = 60) -> str:
    cur = con.execute(sql, params or [])
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    lines += ["| " + " | ".join(_fmt(v) for v in row) + " |" for row in rows[:limit]]
    if len(rows) > limit:
        lines.append(f"\n_{len(rows) - limit} more rows not shown_")
    return "\n".join(lines)


def run_summary(con: duckdb.DuckDBPyConnection, run_id: str) -> str:
    sections = [
        ("Pipeline run", "SELECT run_id, batch_label, status, started_at, finished_at, "
         "round(date_diff('millisecond', started_at, finished_at) / 1000.0, 1) AS duration_sec, error_message "
         "FROM audit.pipeline_runs WHERE run_id = ?"),
        ("Orchestrated steps", "SELECT step_name, status, round(duration_sec, 2) AS duration_sec, message "
         "FROM audit.step_log WHERE run_id = ? ORDER BY started_at, rowid"),
        ("CSV -> bronze ingestion", "SELECT table_name, regexp_extract(source_file, '[^/]+/[^/]+$') AS source_file, "
         "round(file_size_bytes / 1048576.0, 2) AS size_mb, left(file_sha256, 12) AS sha256_prefix, rows_loaded, ingested_at "
         "FROM audit.ingestion_log WHERE run_id = ? ORDER BY rowid"),
        ("Bronze -> silver (OLTP) load", "SELECT table_name, bronze_rows, exact_duplicates, archived_versions, "
         "quarantined_rows, loaded_rows, invalid_casts FROM audit.silver_load_log WHERE run_id = ? ORDER BY rowid"),
        ("Quarantined records by reason", "SELECT table_name, reason, count(*) AS rows FROM quarantine.rejected_records "
         "WHERE run_id = ? GROUP BY ALL ORDER BY table_name, rows DESC"),
        ("Dimension (SCD) loads", "SELECT dimension, scd_type, new_members, new_versions, type1_updates, unchanged "
         "FROM audit.scd_log WHERE run_id = ? ORDER BY rowid"),
        ("Fact loads", "SELECT fact_table, staged_rows, inserted_rows, updated_rows, deleted_rows, total_rows "
         "FROM audit.fact_load_log WHERE run_id = ? ORDER BY rowid"),
        ("Data-quality results", "SELECT stage, check_name, severity, failed_rows, "
         "CASE WHEN passed THEN 'PASS' WHEN severity = 'critical' THEN 'FAIL' ELSE 'WARN' END AS result "
         "FROM audit.dq_results WHERE run_id = ? ORDER BY rowid"),
    ]
    out = [f"# Pipeline run `{run_id}`\n"]
    for title, sql in sections:
        out.append(f"## {title}\n\n{to_markdown(con, sql, [run_id], limit=200)}\n")
    out.append("## Row counts after the run\n\n" + to_markdown(con, f"SELECT layer, table_name, rows FROM ({row_counts_sql(con)})", limit=200) + "\n")
    return "\n".join(out)


def row_counts_sql(con: duckdb.DuckDBPyConnection) -> str:
    """Exact row counts of every bronze / silver / stage / gold table."""
    tables = con.execute(
        """
        SELECT schema_name, table_name FROM duckdb_tables()
        WHERE schema_name IN ('bronze', 'silver', 'stage', 'gold') AND table_name NOT LIKE '%_source'
        ORDER BY CASE schema_name WHEN 'bronze' THEN 1 WHEN 'silver' THEN 2 WHEN 'stage' THEN 3 ELSE 4 END, table_name
        """
    ).fetchall()
    return " UNION ALL ".join(
        f"SELECT {i} AS ord, '{schema}' AS layer, '{table}' AS table_name, count(*) AS rows FROM {schema}.\"{table}\""
        for i, (schema, table) in enumerate(tables)
    ) + " ORDER BY ord"



def business_queries_report(con: duckdb.DuckDBPyConnection) -> str:
    out = [
        "# Business query results\n",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} from the gold star schema. "
        "SQL files: `src/wwi_pipeline/sql/analysis/`._\n",
    ]
    for path in sorted((SQL_DIR / "analysis").glob("*.sql")):
        sql = read_sql(f"analysis/{path.name}")
        title = sql.splitlines()[0].lstrip("- ").strip()
        out.append(f"## {title}\n\n<details><summary>SQL</summary>\n\n```sql\n{sql.strip()}\n```\n</details>\n")
        out.append(to_markdown(con, sql) + "\n")
    return "\n".join(out)


def write_business_report(db_path: Path, out_file: Path) -> Path:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(business_queries_report(con), encoding="utf-8")
    finally:
        con.close()
    return out_file


def write_run_summary(db_path: Path, run_id: str, out_file: Path) -> Path:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(run_summary(con, run_id), encoding="utf-8")
    finally:
        con.close()
    return out_file
