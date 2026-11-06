"""Gold layer: OLAP staging, dimensions (SCD1/SCD2) and facts."""

from __future__ import annotations

import duckdb

from .db import quote_ident, row_count, run_sql_file, scalar, sql_literal, transaction
from .logging_utils import get_logger
from .scd import DimensionSpec, apply_scd

log = get_logger()

# --------------------------------------------------------------------------- dimensions
DIMENSIONS: list[DimensionSpec] = [
    DimensionSpec(
        name="dim_city",
        stage_table="city",
        surrogate_key="city_key",
        business_key="city_id",
        type2=(),
        type1=("city", "state_province_code", "state_province", "sales_territory", "country", "continent",
               "region", "subregion", "latitude", "longitude", "latest_recorded_population"),
    ),
    DimensionSpec(
        name="dim_customer",
        stage_table="customer",
        surrogate_key="customer_key",
        business_key="customer_id",
        type2=("customer_category", "buying_group", "bill_to_customer_id", "delivery_city_id", "delivery_city",
               "delivery_state_province", "delivery_postal_code", "credit_limit", "payment_days",
               "standard_discount_percentage"),
        type1=("customer_name", "bill_to_customer_name", "primary_contact", "delivery_method", "phone_number",
               "website_url", "account_opened_date", "is_on_credit_hold", "is_statement_sent"),
    ),
    DimensionSpec(
        name="dim_employee",
        stage_table="employee",
        surrogate_key="employee_key",
        business_key="employee_id",
        type2=(),
        type1=("full_name", "preferred_name", "is_salesperson", "email_address", "phone_number"),
    ),
    DimensionSpec(
        name="dim_stock_item",
        stage_table="stock_item",
        surrogate_key="stock_item_key",
        business_key="stock_item_id",
        type2=("brand", "size", "color", "selling_package", "buying_package", "supplier_id", "supplier_name",
               "is_chiller_stock", "tax_rate", "unit_price", "recommended_retail_price"),
        type1=("stock_item_name", "primary_stock_group", "stock_groups", "barcode", "lead_time_days",
               "quantity_per_outer", "typical_weight_per_unit"),
    ),
    DimensionSpec(
        name="dim_delivery_method",
        stage_table="delivery_method",
        surrogate_key="delivery_method_key",
        business_key="delivery_method_id",
        type2=(),
        type1=("delivery_method",),
    ),
]

# --------------------------------------------------------------------------- facts
FACTS = {
    # fact table: (source sql file, staged source table, grain key)
    "fact_order": ("gold/10_fact_order_source.sql", "fact_order_source", "order_line_id"),
    "fact_sale": ("gold/11_fact_sale_source.sql", "fact_sale_source", "invoice_line_id"),
}


def prepare_olap(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Create gold objects (idempotent) and rebuild the OLAP staging tables from silver."""
    run_sql_file(con, "gold/00_olap_ddl.sql")
    run_sql_file(con, "gold/01_stage.sql")
    counts = {}
    for table in ("city", "customer", "employee", "stock_item", "delivery_method", "order_line", "sale"):
        counts[f"stage.{table}"] = row_count(con, "stage", table)
        log.info("  stage.%-20s %10d rows", table, counts[f"stage.{table}"])
    return counts


def load_dimensions(con: duckdb.DuckDBPyConnection, run_id: str, run_ts: str) -> dict[str, dict[str, int]]:
    with transaction(con):
        run_sql_file(con, "gold/02_dim_date.sql")
    log.info("  gold.dim_date               %d rows", row_count(con, "gold", "dim_date"))
    return {spec.name: apply_scd(con, spec, run_id, run_ts) for spec in DIMENSIONS}


def merge_fact(con: duckdb.DuckDBPyConnection, fact: str, run_id: str) -> dict[str, int]:
    sql_file, source, grain = FACTS[fact]
    run_sql_file(con, sql_file)
    src, tgt, key = f"stage.{quote_ident(source)}", f"gold.{quote_ident(fact)}", quote_ident(grain)
    cols = [
        r[0]
        for r in con.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='stage' AND table_name=? "
            "ORDER BY ordinal_position",
            [source],
        ).fetchall()
    ]
    stats = {
        "staged_rows": scalar(con, f"SELECT count(*) FROM {src}"),
        "inserted_rows": scalar(con, f"SELECT count(*) FROM {src} s ANTI JOIN {tgt} t ON t.{key} = s.{key}"),
        "updated_rows": scalar(
            con, f"SELECT count(*) FROM {src} s JOIN {tgt} t ON t.{key} = s.{key} WHERE t._row_hash <> s._row_hash"
        ),
        "deleted_rows": scalar(con, f"SELECT count(*) FROM {tgt} t ANTI JOIN {src} s ON t.{key} = s.{key}"),
    }
    col_list = ", ".join(quote_ident(c) for c in cols)
    set_list = ", ".join(f"{quote_ident(c)} = s.{quote_ident(c)}" for c in cols if c != grain)
    run_lit = sql_literal(run_id)
    with transaction(con):
        # Upsert keyed on the grain: new lines inserted, changed lines updated
        # (row hash differs, e.g. re-pointed to a new SCD2 version), lines no
        # longer present in the OLTP source deleted, unchanged lines untouched.
        con.execute(
            f"""
            MERGE INTO {tgt} AS t
            USING {src} AS s
            ON t.{key} = s.{key}
            WHEN MATCHED AND t._row_hash <> s._row_hash THEN
                UPDATE SET {set_list}, _run_id = {run_lit}, _loaded_at = now()
            WHEN NOT MATCHED THEN
                INSERT ({col_list}, _run_id, _loaded_at)
                VALUES ({', '.join('s.' + quote_ident(c) for c in cols)}, {run_lit}, now())
            WHEN NOT MATCHED BY SOURCE THEN DELETE
            """
        )
    stats["total_rows"] = row_count(con, "gold", fact)
    stats = {k: int(v) for k, v in stats.items()}
    con.execute(
        "INSERT INTO audit.fact_load_log VALUES (?, ?, ?, ?, ?, ?, ?, now())",
        [run_id, fact, stats["staged_rows"], stats["inserted_rows"], stats["updated_rows"], stats["deleted_rows"],
         stats["total_rows"]],
    )
    log.info(
        "  gold.%-12s staged=%-9d inserted=%-9d updated=%-7d deleted=%-5d total=%d",
        fact, stats["staged_rows"], stats["inserted_rows"], stats["updated_rows"], stats["deleted_rows"],
        stats["total_rows"],
    )
    return stats


def load_facts(con: duckdb.DuckDBPyConnection, run_id: str) -> dict[str, dict[str, int]]:
    return {fact: merge_fact(con, fact, run_id) for fact in FACTS}
