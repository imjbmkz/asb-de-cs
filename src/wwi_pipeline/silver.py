"""Silver layer = OLTP database.  Bronze (VARCHAR) -> typed, constrained tables.

The table definitions in ``sql/silver/01_oltp_ddl.sql`` are the single source of
truth.  For every table (in foreign-key order) the loader:

1. casts each bronze column to the type declared in the DDL
   (empty string -> NULL, unparsable value -> NULL and counted as invalid cast);
2. drops exact duplicate rows (identical in every source column);
3. validates NOT NULL, CHECK and FOREIGN KEY constraints read from the DuckDB
   catalog; failing rows are written to ``quarantine.rejected_records`` with
   the reason and the original (raw) record;
4. resolves duplicate business keys (PRIMARY KEY / UNIQUE):
     - temporal tables (valid_from/valid_to): the current version
       (latest valid_to, then latest valid_from) is loaded, the other
       versions are written to ``silver.<table>_archive``;
     - other tables: the latest ``last_edited_when`` wins, the rest is
       quarantined as duplicate key;
5. inserts the surviving rows - DuckDB enforces the constraints again.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import duckdb

from .db import log_metric, quote_ident, run_sql_file, scalar, sql_literal, table_exists
from .logging_utils import get_logger
from .sources import SOURCES

log = get_logger()


def to_snake(name: str) -> str:
    """CustomerID -> customer_id, WebsiteURL -> website_url, IsoAlpha3Code -> iso_alpha3_code."""
    name = name.strip().lstrip("﻿")
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()


@dataclass
class TableMeta:
    table: str
    columns: list[tuple[str, str, bool]]  # (name, data_type, nullable)
    keys: list[list[str]] = field(default_factory=list)  # PK first, then UNIQUE
    checks: list[str] = field(default_factory=list)
    fks: list[tuple[list[str], str, list[str]]] = field(default_factory=list)

    @property
    def column_names(self) -> list[str]:
        return [c[0] for c in self.columns]

    @property
    def is_temporal(self) -> bool:
        return {"valid_from", "valid_to"} <= set(self.column_names)


def table_meta(con: duckdb.DuckDBPyConnection, table: str) -> TableMeta:
    cols = con.execute(
        """
        SELECT column_name, data_type, is_nullable = 'YES'
        FROM information_schema.columns
        WHERE table_schema = 'silver' AND table_name = ?
        ORDER BY ordinal_position
        """,
        [table],
    ).fetchall()
    meta = TableMeta(table, [(c[0], c[1], c[2]) for c in cols])
    rows = con.execute(
        """
        SELECT constraint_type, constraint_column_names, expression, referenced_table, referenced_column_names
        FROM duckdb_constraints()
        WHERE schema_name = 'silver' AND table_name = ?
        ORDER BY constraint_type = 'PRIMARY KEY' DESC, constraint_index
        """,
        [table],
    ).fetchall()
    for ctype, colnames, expression, ref_table, ref_cols in rows:
        if ctype in ("PRIMARY KEY", "UNIQUE"):
            if list(colnames) not in meta.keys:
                meta.keys.append(list(colnames))
        elif ctype == "CHECK":
            meta.checks.append(expression)
        elif ctype == "FOREIGN KEY":
            meta.fks.append((list(colnames), ref_table, list(ref_cols)))
    return meta


def cast_expression(raw: str, data_type: str) -> str:
    dt = data_type.upper()
    if dt in ("INTEGER", "BIGINT", "SMALLINT", "TINYINT", "HUGEINT"):
        return f"TRY_CAST(util.to_bigint({raw}) AS {dt})"
    if dt.startswith("DECIMAL") or dt in ("DOUBLE", "FLOAT", "REAL"):
        return f"TRY_CAST(util.clean({raw}) AS {dt})"
    if dt == "BOOLEAN":
        return f"util.to_bool({raw})"
    if dt == "TIMESTAMP":
        return f"util.to_ts({raw})"
    if dt == "DATE":
        return f"CAST(util.to_ts({raw}) AS DATE)"
    if dt == "VARCHAR":
        return f"nullif({raw}, '')"  # original value preserved, only '' -> NULL
    return f"TRY_CAST(util.clean({raw}) AS {dt})"


def _bronze_columns(con: duckdb.DuckDBPyConnection, table: str) -> dict[str, str]:
    """{snake_case_name: original bronze column name} (metadata columns excluded)."""
    rows = con.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='bronze' AND table_name=? ORDER BY ordinal_position",
        [table],
    ).fetchall()
    return {to_snake(r[0]): r[0] for r in rows if not r[0].startswith("_")}


def _quarantine(con: duckdb.DuckDBPyConnection, run_id: str, table: str, where: str) -> int:
    """Copy raw bronze rows of _silver_candidates matching ``where`` into quarantine."""
    n = int(scalar(con, f"SELECT count(*) FROM _silver_candidates c WHERE {where}"))
    if n:
        con.execute(
            f"""
            INSERT INTO quarantine.rejected_records
            SELECT {sql_literal(run_id)}, {sql_literal(table)}, c._reject_reason,
                   to_json(b), now()
            FROM _silver_candidates c
            JOIN bronze.{quote_ident(table)} b ON b.rowid = c._bronze_rowid
            WHERE {where}
            """
        )
    return n


def load_table(con: duckdb.DuckDBPyConnection, table: str, run_id: str) -> dict[str, int]:
    meta = table_meta(con, table)
    if not table_exists(con, "bronze", table):
        log.warning("  silver.%-34s source file not supplied - table left empty", table)
        return {"bronze_rows": 0, "loaded_rows": 0}

    src_cols = _bronze_columns(con, table)
    missing = [c for c in meta.column_names if c not in src_cols]
    if missing:
        raise ValueError(f"bronze.{table} is missing expected columns: {missing}")

    # ---- 1. typed projection + exact-duplicate detection --------------------
    select_typed = ",\n".join(
        f"{cast_expression('b.' + quote_ident(src_cols[c]), t)} AS {quote_ident(c)}" for c, t, _ in meta.columns
    )
    invalid_cast_flags = " + ".join(
        f"(CASE WHEN util.clean(b.{quote_ident(src_cols[c])}) IS NOT NULL AND "
        f"{cast_expression('b.' + quote_ident(src_cols[c]), t)} IS NULL THEN 1 ELSE 0 END)"
        for c, t, _ in meta.columns
        if t.upper() != "VARCHAR"
    ) or "0"
    raw_cols = ", ".join(f"b.{quote_ident(src_cols[c])}" for c in meta.column_names)

    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _silver_typed AS
        SELECT {select_typed},
               b.rowid AS _bronze_rowid,
               {invalid_cast_flags} AS _invalid_casts,
               row_number() OVER (PARTITION BY {raw_cols} ORDER BY b.rowid) AS _dup_rank
        FROM bronze.{quote_ident(table)} b
        """
    )

    # ---- 2/3. constraint validation ----------------------------------------
    reasons: list[str] = []
    for c, _, nullable in meta.columns:
        if not nullable:
            reasons.append(f"CASE WHEN t.{quote_ident(c)} IS NULL THEN '{c} is null or invalid' END")
    for expr in meta.checks:
        reasons.append(f"CASE WHEN NOT coalesce(({expr}), TRUE) THEN {sql_literal('check failed: ' + expr)} END")

    joins: list[str] = []
    for i, (cols, ref_table, ref_cols) in enumerate(meta.fks):
        alias = f"_fk{i}"
        ref_select = ", ".join(f"{quote_ident(rc)} AS {alias}_{j}" for j, rc in enumerate(ref_cols))
        on = " AND ".join(f"t.{quote_ident(c)} = {alias}.{alias}_{j}" for j, c in enumerate(cols))
        joins.append(
            f"LEFT JOIN (SELECT DISTINCT {ref_select}, TRUE AS {alias}_hit FROM silver.{quote_ident(ref_table)}) {alias} ON {on}"
        )
        not_null = " AND ".join(f"t.{quote_ident(c)} IS NOT NULL" for c in cols)
        reasons.append(
            f"CASE WHEN {not_null} AND {alias}.{alias}_hit IS NULL "
            f"THEN {sql_literal(f'foreign key ({", ".join(cols)}) not found in {ref_table}')} END"
        )

    reason_expr = f"nullif(concat_ws('; ', {', '.join(reasons)}), '')" if reasons else "NULL::VARCHAR"

    # Ordering that decides which row wins when a business key is duplicated.
    if meta.is_temporal:
        order = "t.valid_to DESC NULLS LAST, t.valid_from DESC NULLS LAST, t._bronze_rowid DESC"
    elif "last_edited_when" in meta.column_names:
        order = "t.last_edited_when DESC NULLS LAST, t._bronze_rowid DESC"
    else:
        order = "t._bronze_rowid DESC"

    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _silver_validated AS
        SELECT t.*, {reason_expr} AS _reject_reason
        FROM _silver_typed t
        {' '.join(joins)}
        WHERE t._dup_rank = 1
        """
    )
    # A row loses if ANY of its keys (PK or UNIQUE) is taken by a better row.
    key_ranks = [
        f"row_number() OVER (PARTITION BY {', '.join('t.' + quote_ident(k) for k in key)} "
        f"ORDER BY {order})"
        for key in meta.keys
    ] or ["1"]
    con.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE _silver_candidates AS
        SELECT t.*, greatest({', '.join(key_ranks)}) AS _key_rank
        FROM _silver_validated t
        """
    )

    stats = {
        "bronze_rows": int(scalar(con, "SELECT count(*) FROM _silver_typed")),
        "exact_duplicates": int(scalar(con, "SELECT count(*) FROM _silver_typed WHERE _dup_rank > 1")),
        "invalid_casts": int(scalar(con, "SELECT coalesce(sum(_invalid_casts), 0) FROM _silver_typed")),
    }

    # ---- quarantine: constraint failures + (non-temporal) duplicate keys ------
    # The winning version of a key is chosen on recency only; if that version is
    # invalid the key is quarantined (an older valid version is NOT promoted).
    stats["quarantined_rows"] = _quarantine(con, run_id, table, "c._reject_reason IS NOT NULL")
    if not meta.is_temporal:
        con.execute(
            "UPDATE _silver_candidates SET _reject_reason = 'duplicate business key' "
            "WHERE _reject_reason IS NULL AND _key_rank > 1"
        )
        stats["quarantined_rows"] += _quarantine(con, run_id, table, "c._reject_reason = 'duplicate business key'")

    # ---- 4. archive older versions of temporal tables -------------------------
    col_list = ", ".join(quote_ident(c) for c in meta.column_names)
    stats["archived_versions"] = 0
    if meta.is_temporal:
        con.execute(
            f"CREATE TABLE IF NOT EXISTS silver.{quote_ident(table + '_archive')} AS "
            f"SELECT * FROM silver.{quote_ident(table)} LIMIT 0"
        )
        con.execute(
            f"INSERT INTO silver.{quote_ident(table + '_archive')} ({col_list}) "
            f"SELECT {col_list} FROM _silver_candidates WHERE _reject_reason IS NULL AND _key_rank > 1"
        )
        stats["archived_versions"] = int(
            scalar(con, "SELECT count(*) FROM _silver_candidates WHERE _reject_reason IS NULL AND _key_rank > 1")
        )

    # ---- 5. load ---------------------------------------------------------------
    con.execute(
        f"INSERT INTO silver.{quote_ident(table)} ({col_list}) "
        f"SELECT {col_list} FROM _silver_candidates WHERE _reject_reason IS NULL AND _key_rank = 1"
    )
    stats["loaded_rows"] = int(scalar(con, f"SELECT count(*) FROM silver.{quote_ident(table)}"))
    con.execute("DROP TABLE IF EXISTS _silver_typed; DROP TABLE IF EXISTS _silver_validated; DROP TABLE IF EXISTS _silver_candidates")
    return stats


def prepare_oltp(con: duckdb.DuckDBPyConnection) -> int:
    """(Re)create the OLTP database objects: parsing macros + table DDL with constraints."""
    run_sql_file(con, "silver/00_macros.sql")
    run_sql_file(con, "silver/01_oltp_ddl.sql")
    return int(scalar(con, "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'silver'"))


def load_oltp(con: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, dict[str, int]]:
    results: dict[str, dict[str, int]] = {}
    for source in SOURCES:  # FK dependency order
        stats = load_table(con, source.table, run_id)
        results[source.table] = stats
        con.execute(
            "INSERT INTO audit.silver_load_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, now())",
            [
                run_id,
                source.table,
                stats.get("bronze_rows", 0),
                stats.get("exact_duplicates", 0),
                stats.get("archived_versions", 0),
                stats.get("quarantined_rows", 0),
                stats.get("loaded_rows", 0),
                stats.get("invalid_casts", 0),
            ],
        )
        log_metric(con, run_id, "load_oltp", f"silver.{source.table}.rows", stats.get("loaded_rows", 0))
        log.info(
            "  silver.%-34s loaded=%-9d archived=%-6d quarantined=%-5d dup=%-4d invalid_casts=%d",
            source.table,
            stats.get("loaded_rows", 0),
            stats.get("archived_versions", 0),
            stats.get("quarantined_rows", 0),
            stats.get("exact_duplicates", 0),
            stats.get("invalid_casts", 0),
        )
    return results
