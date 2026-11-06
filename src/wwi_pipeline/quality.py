"""Data-quality checks.

Every check is a SQL query returning the number of offending rows.

* ``critical`` checks stop the pipeline (the run is recorded as FAILED, nothing
  downstream runs).  Because silver is rebuilt and gold changes are applied in
  transactions per step, a failed run never leaves half-written tables behind.
* ``warning`` checks are recorded and logged but do not stop the run.

Invalid records are not silently dropped: the silver loader quarantines them in
``quarantine.rejected_records`` (with reason + raw record) and the checks below
make sure the quarantine stays within tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass

import duckdb

from .logging_utils import get_logger

log = get_logger()

MAX_QUARANTINE_SHARE = 0.05  # > 5 % of a table rejected => critical


class DataQualityError(RuntimeError):
    pass


@dataclass(frozen=True)
class Check:
    name: str
    severity: str  # critical | warning
    sql: str  # returns a single integer: number of failing rows
    description: str


def _unique(table: str, cols: str) -> str:
    return f"SELECT count(*) FROM (SELECT {cols} FROM {table} GROUP BY {cols} HAVING count(*) > 1)"


def _not_null(table: str, col: str) -> str:
    return f"SELECT count(*) FROM {table} WHERE {col} IS NULL"


# --------------------------------------------------------------------------- OLTP (silver)
OLTP_CHECKS: list[Check] = [
    *[
        Check(f"pk_not_null:{t}", "critical", _not_null(f"silver.{t}", c), f"{t}.{c} must not be NULL")
        for t, c in [
            ("sales_customers", "customer_id"), ("warehouse_stockitems", "stock_item_id"),
            ("application_people", "person_id"), ("application_cities", "city_id"),
            ("sales_orders", "order_id"), ("sales_orderlines", "order_line_id"),
            ("sales_invoices", "invoice_id"), ("sales_invoicelines", "invoice_line_id"),
        ]
    ],
    *[
        Check(f"unique_key:{t}", "critical", _unique(f"silver.{t}", c), f"{t}.{c} must be unique")
        for t, c in [
            ("sales_customers", "customer_id"), ("warehouse_stockitems", "stock_item_id"),
            ("application_people", "person_id"), ("sales_orders", "order_id"),
            ("sales_orderlines", "order_line_id"), ("sales_invoices", "invoice_id"),
            ("sales_invoicelines", "invoice_line_id"),
        ]
    ],
    Check(
        "fk:customers.bill_to_customer_id", "critical",
        "SELECT count(*) FROM silver.sales_customers c ANTI JOIN silver.sales_customers b "
        "ON b.customer_id = c.bill_to_customer_id",
        "Every bill-to customer must exist",
    ),
    Check(
        "fk:orders.backorder_order_id", "warning",
        "SELECT count(*) FROM silver.sales_orders o WHERE backorder_order_id IS NOT NULL AND NOT EXISTS "
        "(SELECT 1 FROM silver.sales_orders b WHERE b.order_id = o.backorder_order_id)",
        "Backorders should reference an existing order",
    ),
    Check("valid:orderlines.quantity>0", "critical",
          "SELECT count(*) FROM silver.sales_orderlines WHERE quantity <= 0", "Ordered quantity must be positive"),
    Check("valid:orderlines.picked<=quantity", "warning",
          "SELECT count(*) FROM silver.sales_orderlines WHERE picked_quantity > quantity",
          "Picked quantity should not exceed ordered quantity"),
    Check("valid:invoicelines.quantity", "critical",
          "SELECT count(*) FROM silver.sales_invoicelines il JOIN silver.sales_invoices i USING (invoice_id) "
          "WHERE (NOT i.is_credit_note AND il.quantity <= 0)",
          "Invoiced quantity must be positive (except credit notes)"),
    Check("valid:invoicelines.amounts", "warning",
          "SELECT count(*) FROM silver.sales_invoicelines "
          "WHERE abs(extended_price - (quantity * unit_price + tax_amount)) > 0.05",
          "Extended price should equal quantity * unit price + tax"),
    Check("valid:prices>=0", "critical",
          "SELECT (SELECT count(*) FROM silver.sales_orderlines WHERE unit_price < 0) + "
          "(SELECT count(*) FROM silver.sales_invoicelines WHERE unit_price < 0 OR tax_amount < 0)",
          "Unit prices and tax amounts must not be negative"),
    Check("valid:transaction_dates_in_range", "critical",
          "SELECT (SELECT count(*) FROM silver.sales_orders WHERE order_date NOT BETWEEN DATE '2000-01-01' AND current_date) + "
          "(SELECT count(*) FROM silver.sales_invoices WHERE invoice_date NOT BETWEEN DATE '2000-01-01' AND current_date)",
          "Order and invoice dates must be valid, realistic dates"),
    Check("sequence:expected_delivery>=order_date", "warning",
          "SELECT count(*) FROM silver.sales_orders WHERE expected_delivery_date < order_date",
          "Expected delivery cannot precede the order"),
    Check("sequence:invoice_date>=order_date", "critical",
          "SELECT count(*) FROM silver.sales_invoices i JOIN silver.sales_orders o USING (order_id) "
          "WHERE i.invoice_date < o.order_date",
          "An order cannot be invoiced before it is placed"),
    Check("sequence:delivery>=invoice_date", "warning",
          "SELECT count(*) FROM silver.sales_invoices WHERE CAST(confirmed_delivery_time AS DATE) < invoice_date",
          "Delivery cannot precede the invoice"),
    Check("reconcile:bronze=silver+archive+quarantine+duplicates", "critical",
          "SELECT count(*) FROM audit.silver_load_log WHERE run_id = $run_id AND "
          "bronze_rows <> loaded_rows + archived_versions + quarantined_rows + exact_duplicates",
          "Every bronze row must be accounted for (loaded, archived, quarantined or exact duplicate)"),
    Check("quarantine:share_within_tolerance", "critical",
          f"SELECT count(*) FROM audit.silver_load_log WHERE run_id = $run_id AND bronze_rows > 0 "
          f"AND quarantined_rows > {MAX_QUARANTINE_SHARE} * bronze_rows",
          f"No table may have more than {MAX_QUARANTINE_SHARE:.0%} of its rows quarantined"),
    Check("quarantine:rows_this_run", "warning",
          "SELECT count(*) FROM quarantine.rejected_records WHERE run_id = $run_id",
          "Rows rejected into quarantine during this run (inspect quarantine.rejected_records)"),
    Check("required_tables_not_empty", "critical",
          "SELECT (SELECT count(*) = 0 FROM silver.sales_customers)::INT + (SELECT count(*) = 0 FROM silver.sales_orders)::INT"
          " + (SELECT count(*) = 0 FROM silver.sales_invoicelines)::INT + (SELECT count(*) = 0 FROM silver.warehouse_stockitems)::INT",
          "Core OLTP tables must contain data"),
]


# --------------------------------------------------------------------------- final (gold)
def _dimension_checks(dim: str, sk: str, nk: str, scd2: bool) -> list[Check]:
    t = f"gold.{dim}"
    checks = [
        Check(f"unique_surrogate_key:{dim}", "critical", _unique(t, sk), f"{dim}.{sk} must be unique"),
        Check(f"not_null_business_key:{dim}", "critical", _not_null(t, nk), f"{dim}.{nk} must not be NULL"),
        Check(f"one_current_version:{dim}", "critical",
              f"SELECT count(*) FROM (SELECT {nk} FROM {t} GROUP BY {nk} HAVING count(*) FILTER (WHERE is_current) <> 1)",
              f"Exactly one current row per {nk}"),
        Check(f"valid_range:{dim}", "critical", f"SELECT count(*) FROM {t} WHERE valid_from >= valid_to",
              "valid_from must be earlier than valid_to"),
    ]
    if scd2:
        checks += [
            Check(f"no_overlap:{dim}", "critical",
                  f"SELECT count(*) FROM {t} a JOIN {t} b ON a.{nk} = b.{nk} AND a.{sk} < b.{sk} "
                  f"AND a.valid_from < b.valid_to AND b.valid_from < a.valid_to",
                  "SCD2 validity ranges of a business key must not overlap"),
            Check(f"no_gaps:{dim}", "critical",
                  f"SELECT count(*) FROM (SELECT valid_to, lead(valid_from) OVER (PARTITION BY {nk} ORDER BY valid_from) AS nxt "
                  f"FROM {t}) WHERE nxt IS NOT NULL AND nxt <> valid_to",
                  "Consecutive SCD2 versions must be contiguous"),
            Check(f"current_is_open:{dim}", "critical",
                  f"SELECT count(*) FROM {t} WHERE is_current <> (valid_to = TIMESTAMP '9999-12-31')",
                  "Only the open-ended version is current"),
            Check(f"no_redundant_versions:{dim}", "critical",
                  f"SELECT count(*) FROM (SELECT _t2_hash, lag(_t2_hash) OVER (PARTITION BY {nk} ORDER BY valid_from) AS prev "
                  f"FROM {t} WHERE {sk} <> 0) WHERE _t2_hash = prev",
                  "A new version is only created when a tracked attribute changes (re-runs add no versions)"),
        ]
    return checks


FINAL_CHECKS: list[Check] = [
    *_dimension_checks("dim_city", "city_key", "city_id", False),
    *_dimension_checks("dim_customer", "customer_key", "customer_id", True),
    *_dimension_checks("dim_employee", "employee_key", "employee_id", False),
    *_dimension_checks("dim_stock_item", "stock_item_key", "stock_item_id", True),
    *_dimension_checks("dim_delivery_method", "delivery_method_key", "delivery_method_id", False),
    Check("dim_date:fiscal_year_rule", "critical",
          "SELECT count(*) FROM gold.dim_date WHERE date_key > 0 AND ("
          "(month(date) >= 11 AND (fiscal_year <> year(date) + 1 OR fiscal_month <> month(date) - 10)) OR "
          "(month(date) < 11 AND (fiscal_year <> year(date) OR fiscal_month <> month(date) + 2)))",
          "Fiscal year starts 1 November (FY named after the ending calendar year)"),
    Check("unique_grain:fact_order", "critical", _unique("gold.fact_order", "order_line_id"),
          "fact_order: one row per order line"),
    Check("unique_grain:fact_sale", "critical", _unique("gold.fact_sale", "invoice_line_id"),
          "fact_sale: one row per invoice line"),
    Check("completeness:fact_order=stage", "critical",
          "SELECT abs((SELECT count(*) FROM gold.fact_order) - (SELECT count(*) FROM stage.order_line))",
          "Every staged order line is loaded exactly once"),
    Check("completeness:fact_sale=stage", "critical",
          "SELECT abs((SELECT count(*) FROM gold.fact_sale) - (SELECT count(*) FROM stage.sale))",
          "Every staged invoice line is loaded exactly once"),
    Check("reconcile:fact_sale_amount=oltp", "critical",
          "SELECT CASE WHEN abs((SELECT coalesce(sum(total_including_tax), 0) FROM gold.fact_sale) - "
          "(SELECT coalesce(sum(extended_price), 0) FROM silver.sales_invoicelines)) > 0.01 THEN 1 ELSE 0 END",
          "Sales amount in the warehouse equals the OLTP invoice lines"),
    Check("reconcile:fact_order_quantity=oltp", "critical",
          "SELECT CASE WHEN (SELECT coalesce(sum(quantity), 0) FROM gold.fact_order) <> "
          "(SELECT coalesce(sum(quantity), 0) FROM silver.sales_orderlines) THEN 1 ELSE 0 END",
          "Ordered quantity in the warehouse equals the OLTP order lines"),
    Check("fact_keys_not_null:fact_order", "critical",
          "SELECT count(*) FROM gold.fact_order WHERE order_date_key IS NULL OR customer_key IS NULL OR city_key IS NULL "
          "OR salesperson_key IS NULL OR picker_key IS NULL OR stock_item_key IS NULL",
          "Every fact_order row resolves all its dimension keys"),
    Check("fact_keys_not_null:fact_sale", "critical",
          "SELECT count(*) FROM gold.fact_sale WHERE invoice_date_key IS NULL OR customer_key IS NULL "
          "OR bill_to_customer_key IS NULL OR city_key IS NULL OR salesperson_key IS NULL OR stock_item_key IS NULL "
          "OR delivery_method_key IS NULL",
          "Every fact_sale row resolves all its dimension keys"),
    Check("fact_keys_exist:fact_sale", "critical",
          "SELECT count(*) FROM gold.fact_sale f "
          "WHERE NOT EXISTS (SELECT 1 FROM gold.dim_customer d WHERE d.customer_key = f.customer_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_stock_item d WHERE d.stock_item_key = f.stock_item_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_date d WHERE d.date_key = f.invoice_date_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_city d WHERE d.city_key = f.city_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_employee d WHERE d.employee_key = f.salesperson_key)",
          "Every fact_sale foreign key exists in its dimension"),
    Check("fact_keys_exist:fact_order", "critical",
          "SELECT count(*) FROM gold.fact_order f "
          "WHERE NOT EXISTS (SELECT 1 FROM gold.dim_customer d WHERE d.customer_key = f.customer_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_stock_item d WHERE d.stock_item_key = f.stock_item_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_date d WHERE d.date_key = f.order_date_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_city d WHERE d.city_key = f.city_key) "
          "OR NOT EXISTS (SELECT 1 FROM gold.dim_employee d WHERE d.employee_key = f.salesperson_key)",
          "Every fact_order foreign key exists in its dimension"),
    Check("unknown_members:fact_sale", "warning",
          "SELECT count(*) FROM gold.fact_sale WHERE customer_key = 0 OR stock_item_key = 0 OR city_key = 0 "
          "OR salesperson_key = 0 OR delivery_method_key = 0 OR invoice_date_key = -1",
          "fact_sale rows pointing to an Unknown member"),
    Check("unknown_members:fact_order", "warning",
          "SELECT count(*) FROM gold.fact_order WHERE customer_key = 0 OR stock_item_key = 0 OR city_key = 0 "
          "OR salesperson_key = 0 OR order_date_key = -1",
          "fact_order rows pointing to an Unknown member (picker_key 0 = not yet picked is expected)"),
    Check("scd_point_in_time:fact_sale", "critical",
          "SELECT count(*) FROM gold.fact_sale f JOIN gold.dim_customer c USING (customer_key) "
          "JOIN gold.dim_date d ON d.date_key = f.invoice_date_key "
          "JOIN gold.dim_stock_item s USING (stock_item_key) "
          "WHERE f.customer_key <> 0 AND f.stock_item_key <> 0 AND NOT ("
          "CAST(d.date AS TIMESTAMP) >= c.valid_from AND CAST(d.date AS TIMESTAMP) < c.valid_to AND "
          "CAST(d.date AS TIMESTAMP) >= s.valid_from AND CAST(d.date AS TIMESTAMP) < s.valid_to)",
          "Each sale points to the customer / stock item version valid on the invoice date"),
    Check("scd_point_in_time:fact_order", "critical",
          "SELECT count(*) FROM gold.fact_order f JOIN gold.dim_customer c USING (customer_key) "
          "JOIN gold.dim_date d ON d.date_key = f.order_date_key "
          "JOIN gold.dim_stock_item s USING (stock_item_key) "
          "WHERE f.customer_key <> 0 AND f.stock_item_key <> 0 AND NOT ("
          "CAST(d.date AS TIMESTAMP) >= c.valid_from AND CAST(d.date AS TIMESTAMP) < c.valid_to AND "
          "CAST(d.date AS TIMESTAMP) >= s.valid_from AND CAST(d.date AS TIMESTAMP) < s.valid_to)",
          "Each order line points to the customer / stock item version valid on the order date"),
    Check("valid:fact_measures", "critical",
          "SELECT (SELECT count(*) FROM gold.fact_sale WHERE (quantity <= 0 AND NOT is_credit_note) "
          "OR total_including_tax < total_excluding_tax - 0.01 OR tax_amount < 0) + "
          "(SELECT count(*) FROM gold.fact_order WHERE quantity <= 0 OR total_excluding_tax < 0)",
          "Quantities and monetary measures meet basic validity rules"),
]


def run_checks(con: duckdb.DuckDBPyConnection, run_id: str, stage: str, checks: list[Check]) -> list[dict]:
    results, critical_failures = [], []
    for check in checks:
        failed = int(con.execute(check.sql.replace("$run_id", "?"), [run_id] * check.sql.count("$run_id")).fetchone()[0])
        passed = failed == 0
        con.execute(
            "INSERT INTO audit.dq_results VALUES (?, ?, ?, ?, ?, ?, ?, now())",
            [run_id, stage, check.name, check.severity, failed, passed, check.description],
        )
        results.append({"check": check.name, "severity": check.severity, "failed_rows": failed, "passed": passed})
        if passed:
            log.info("  [PASS] %-55s", check.name)
        elif check.severity == "critical":
            log.error("  [FAIL] %-55s failed_rows=%d  (%s)", check.name, failed, check.description)
            critical_failures.append(check.name)
        else:
            log.warning("  [WARN] %-55s failed_rows=%d  (%s)", check.name, failed, check.description)
    if critical_failures:
        raise DataQualityError(f"{len(critical_failures)} critical {stage} check(s) failed: {', '.join(critical_failures)}")
    return results
