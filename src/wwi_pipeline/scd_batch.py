"""Create the second input batch used to demonstrate SCD Type 2.

The Kaggle export is a single snapshot, so - as allowed by the case study - a
small change batch is generated from it *as source files* (never by editing the
warehouse).  It mimics what WWI's system-versioned temporal tables would export
after an update: the edited row becomes the new current version
(ValidFrom = effective date, ValidTo = 9999-12-31) and the previous version is
added as a historical row (ValidTo = effective date).

Business keys are never changed.  The batch directory only contains the changed
files; ``run --batch-dir`` overlays them on top of the raw directory.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

import duckdb

from .db import path_for_sql, quote_ident, sql_literal
from .logging_utils import get_logger
from .sources import SOURCES_BY_TABLE, find_file

log = get_logger()


@dataclass(frozen=True)
class Change:
    table: str
    key_column: str
    key_value: str
    column: str
    new_value: str
    scd: str  # expected handling in the warehouse
    note: str


# Selected customers / stock items have invoices both before and after the
# effective date so the point-in-time fact resolution can be observed.
DEFAULT_CHANGES: list[Change] = [
    Change("sales_customers", "CustomerID", "74", "CustomerCategoryID", "4", "SCD2",
           "Tailspin Toys (Indios, PR): category Novelty Shop -> Supermarket"),
    Change("sales_customers", "CustomerID", "62", "BuyingGroupID", "2.0", "SCD2",
           "Tailspin Toys (Great Neck Estates, NY): buying group Tailspin Toys -> Wingtip Toys"),
    Change("sales_customers", "CustomerID", "14", "CreditLimit", "5000.0", "SCD2",
           "Tailspin Toys (Long Meadow, MD): credit limit (none) -> 5000"),
    Change("sales_customers", "CustomerID", "14", "PaymentDays", "30", "SCD2",
           "Tailspin Toys (Long Meadow, MD): payment days 7 -> 30"),
    Change("sales_customers", "CustomerID", "2", "PhoneNumber", "(406) 555-0100", "SCD1",
           "Tailspin Toys (Sylvanite, MT): phone number corrected (overwrite, no new version)"),
    Change("warehouse_stockitems", "StockItemID", "4", "Brand", "Northwind", "SCD2",
           "USB food flash drive - sushi roll: brand (none) -> Northwind"),
    Change("warehouse_stockitems", "StockItemID", "10", "UnitPrice", "35.0", "SCD2",
           "USB food flash drive - chocolate bar: unit price 32.00 -> 35.00"),
    Change("warehouse_stockitems", "StockItemID", "97", "LeadTimeDays", "21", "SCD1",
           "\"The Gu\" red shirt XML tag t-shirt (Black) 3XL: lead time 14 -> 21 days (overwrite)"),
]


def _fmt(d: date) -> str:
    return d.strftime("%d-%m-%Y 00:00:00")  # same day-first format as the export


def make_scd_batch(raw_dir: Path, out_dir: Path, effective: date = date(2016, 7, 15),
                   changes: list[Change] | None = None) -> Path:
    changes = changes or DEFAULT_CHANGES
    out_dir.mkdir(parents=True, exist_ok=True)
    eff = sql_literal(_fmt(effective))
    con = duckdb.connect()
    for table in sorted({c.table for c in changes}):
        source = find_file(raw_dir, SOURCES_BY_TABLE[table])
        if source is None:
            raise FileNotFoundError(f"{table}.csv not found in {raw_dir}")
        table_changes = [c for c in changes if c.table == table]
        key_col = table_changes[0].key_column
        keys = sorted({c.key_value for c in table_changes})
        key_list = ", ".join(sql_literal(k) for k in keys)

        con.execute(f"CREATE OR REPLACE TABLE src AS SELECT * FROM read_csv({path_for_sql(source)}, header=true, all_varchar=true)")
        columns = [r[0] for r in con.execute("DESCRIBE src").fetchall()]
        # current row = open-ended version (ValidTo year 9999)
        is_target = f"{quote_ident(key_col)} IN ({key_list}) AND ValidTo LIKE '%-9999 %'"

        replaced = []
        for col in columns:
            expr = quote_ident(col)
            for c in (c for c in table_changes if c.column == col):
                expr = f"CASE WHEN {quote_ident(key_col)} = {sql_literal(c.key_value)} THEN {sql_literal(c.new_value)} ELSE {expr} END"
            if col == "ValidFrom":
                expr = eff
            replaced.append(f"{expr} AS {quote_ident(col)}")
        historical = [f"{eff} AS {quote_ident(c)}" if c == "ValidTo" else quote_ident(c) for c in columns]

        target = out_dir / f"{table}.csv"
        con.execute(
            f"""
            COPY (
                SELECT * FROM src WHERE NOT ({is_target})
                UNION ALL
                SELECT {', '.join(historical)} FROM src WHERE {is_target}    -- previous version, now closed
                UNION ALL
                SELECT {', '.join(replaced)} FROM src WHERE {is_target}      -- new current version
            ) TO {path_for_sql(target)} (HEADER, DELIMITER ',', QUOTE '"')
            """
        )
        log.info("  wrote %s (%d changed keys)", target, len(keys))

    manifest = {"effective_date": effective.isoformat(), "changes": [asdict(c) for c in changes]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    con.close()
    return out_dir
