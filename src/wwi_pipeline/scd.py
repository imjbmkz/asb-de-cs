"""Generic Slowly Changing Dimension merge (Type 1 + Type 2) executed in DuckDB.

For a staging table with one row per business key:

Surrogate keys are assigned deterministically as max(existing key) + row_number()
ordered by business key (single-writer pipeline), so rebuilding from scratch
reproduces identical keys.

* new business key            -> insert first version, valid_from = 1900-01-01
                                 (back-dated so every historical fact resolves)
* type-2 attribute changed    -> close the current version (valid_to = effective ts,
                                 is_current = FALSE) and insert a new current version
                                 with a new surrogate key
* only type-1 attribute changed -> overwrite in place on ALL versions of the key
* nothing changed             -> no-op  (re-running the same input is idempotent)

The effective timestamp of a type-2 change is the source system's change
timestamp (ValidFrom of the temporal OLTP row) when it is later than the
current version's valid_from; otherwise the pipeline run timestamp is used.
Validity intervals are half-open: [valid_from, valid_to).

Business keys missing from staging are left untouched (no hard/soft delete).
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from .db import quote_ident, scalar, sql_literal, transaction
from .logging_utils import get_logger

log = get_logger()

OPEN_END = "TIMESTAMP '9999-12-31 00:00:00'"
BEGINNING = "TIMESTAMP '1900-01-01 00:00:00'"


@dataclass(frozen=True)
class DimensionSpec:
    name: str  # gold table, e.g. dim_customer
    stage_table: str  # stage table, e.g. customer
    surrogate_key: str
    business_key: str
    type2: tuple[str, ...]
    type1: tuple[str, ...]
    change_ts: str = "change_ts"

    @property
    def scd_type(self) -> str:
        return "2" if self.type2 else "1"


def _hash(cols: tuple[str, ...], alias: str) -> str:
    if not cols:
        return "'-'"
    fields = ", ".join(f"{c} := {alias}.{quote_ident(c)}" for c in cols)
    return f"md5(CAST(to_json(struct_pack({fields})) AS VARCHAR))"


def apply_scd(con: duckdb.DuckDBPyConnection, spec: DimensionSpec, run_id: str, run_ts: str) -> dict[str, int]:
    dim = f"gold.{quote_ident(spec.name)}"
    sk, nk = quote_ident(spec.surrogate_key), quote_ident(spec.business_key)
    attrs = spec.type2 + spec.type1
    run_id_lit, run_ts_lit = sql_literal(run_id), f"TIMESTAMP {sql_literal(run_ts)}"

    with transaction(con):
        con.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE _scd_cmp AS
            SELECT s.*,
                   {_hash(spec.type2, 's')} AS _new_t2_hash,
                   {_hash(spec.type1, 's')} AS _new_t1_hash,
                   d.{sk}                  AS _cur_key,
                   d.valid_from            AS _cur_from,
                   d._t2_hash              AS _cur_t2_hash,
                   d._t1_hash              AS _cur_t1_hash
            FROM stage.{quote_ident(spec.stage_table)} s
            LEFT JOIN {dim} d ON d.{nk} = s.{nk} AND d.is_current
            """
        )
        stats = {
            "new_members": scalar(con, "SELECT count(*) FROM _scd_cmp WHERE _cur_key IS NULL"),
            "new_versions": scalar(
                con, "SELECT count(*) FROM _scd_cmp WHERE _cur_key IS NOT NULL AND _new_t2_hash <> _cur_t2_hash"
            ),
            "type1_updates": scalar(
                con, "SELECT count(*) FROM _scd_cmp WHERE _cur_key IS NOT NULL AND _new_t1_hash <> _cur_t1_hash"
            ),
        }
        stats["unchanged"] = scalar(
            con,
            "SELECT count(*) FROM _scd_cmp WHERE _cur_key IS NOT NULL "
            "AND _new_t2_hash = _cur_t2_hash AND _new_t1_hash = _cur_t1_hash",
        )

        # 1) Type 1: overwrite type-1 attributes on every version of the key.
        if spec.type1:
            set_t1 = ", ".join(f"{quote_ident(c)} = s.{quote_ident(c)}" for c in spec.type1)
            con.execute(
                f"""
                UPDATE {dim} AS d
                SET {set_t1}, _t1_hash = s._new_t1_hash, _updated_run_id = {run_id_lit}
                FROM _scd_cmp s
                WHERE d.{nk} = s.{nk} AND s._cur_key IS NOT NULL AND s._new_t1_hash <> s._cur_t1_hash
                """
            )

        # 2) Type 2: close the current version.
        effective = (
            f"CASE WHEN s.{quote_ident(spec.change_ts)} > s._cur_from "
            f"THEN s.{quote_ident(spec.change_ts)} ELSE {run_ts_lit} END"
        )
        if spec.type2:
            con.execute(
                f"""
                UPDATE {dim} AS d
                SET valid_to = {effective}, is_current = FALSE, _updated_run_id = {run_id_lit}
                FROM _scd_cmp s
                WHERE d.{sk} = s._cur_key AND s._new_t2_hash <> s._cur_t2_hash
                """
            )

        # 3) Insert new members and new versions.
        col_list = ", ".join(quote_ident(c) for c in attrs)
        sel_list = ", ".join(f"s.{quote_ident(c)}" for c in attrs)
        con.execute(
            f"""
            INSERT INTO {dim} ({sk}, {nk}, {col_list}, valid_from, valid_to, is_current,
                               _t2_hash, _t1_hash, _inserted_run_id, _updated_run_id)
            SELECT (SELECT coalesce(max({sk}), 0) FROM {dim}) + row_number() OVER (ORDER BY s.{nk}),
                   s.{nk}, {sel_list},
                   CASE WHEN s._cur_key IS NULL THEN {BEGINNING} ELSE {effective} END,
                   {OPEN_END}, TRUE, s._new_t2_hash, s._new_t1_hash, {run_id_lit}, {run_id_lit}
            FROM _scd_cmp s
            WHERE s._cur_key IS NULL OR s._new_t2_hash <> s._cur_t2_hash
            """
        )
        con.execute("DROP TABLE IF EXISTS _scd_cmp")

    stats = {k: int(v) for k, v in stats.items()}
    con.execute(
        "INSERT INTO audit.scd_log VALUES (?, ?, ?, ?, ?, ?, ?, now())",
        [run_id, spec.name, f"SCD{spec.scd_type}", stats["new_members"], stats["new_versions"],
         stats["type1_updates"], stats["unchanged"]],
    )
    log.info(
        "  gold.%-22s SCD%s new_members=%-6d new_versions=%-4d type1_updates=%-4d unchanged=%d",
        spec.name, spec.scd_type, stats["new_members"], stats["new_versions"], stats["type1_updates"], stats["unchanged"],
    )
    return stats
