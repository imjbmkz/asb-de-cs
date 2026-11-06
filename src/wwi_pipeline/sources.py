"""Registry of the source CSV files used by the pipeline.

Each entry maps a CSV file of the Kaggle export (named ``<schema>_<table>.csv``
after the original SQL Server schema/table, e.g. ``Sales_Customers.csv``) to a
table name that is used, unchanged, in the bronze and silver layers.

The order of SOURCES is the dependency (foreign-key) order used to load silver.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Source:
    table: str  # bronze/silver table name, e.g. "sales_customers"
    oltp_name: str  # original WideWorldImporters table, e.g. "Sales.Customers"
    required: bool = True

    @property
    def filename(self) -> str:
        return f"{self.table}.csv"


SOURCES: list[Source] = [
    # Application (reference data)
    Source("application_countries", "Application.Countries"),
    Source("application_stateprovinces", "Application.StateProvinces"),
    Source("application_cities", "Application.Cities"),
    Source("application_people", "Application.People"),
    Source("application_deliverymethods", "Application.DeliveryMethods"),
    Source("application_paymentmethods", "Application.PaymentMethods", required=False),
    Source("application_transactiontypes", "Application.TransactionTypes", required=False),
    # Purchasing
    Source("purchasing_suppliercategories", "Purchasing.SupplierCategories"),
    Source("purchasing_suppliers", "Purchasing.Suppliers"),
    # Warehouse
    Source("warehouse_colors", "Warehouse.Colors"),
    Source("warehouse_packagetypes", "Warehouse.PackageTypes"),
    Source("warehouse_stockgroups", "Warehouse.StockGroups"),
    Source("warehouse_stockitems", "Warehouse.StockItems"),
    Source("warehouse_stockitemstockgroups", "Warehouse.StockItemStockGroups"),
    Source("warehouse_stockitemholdings", "Warehouse.StockItemHoldings", required=False),
    # Sales
    Source("sales_customercategories", "Sales.CustomerCategories"),
    Source("sales_buyinggroups", "Sales.BuyingGroups"),
    Source("sales_customers", "Sales.Customers"),
    Source("sales_orders", "Sales.Orders"),
    Source("sales_orderlines", "Sales.OrderLines"),
    Source("sales_invoices", "Sales.Invoices"),
    Source("sales_invoicelines", "Sales.InvoiceLines"),
    Source("sales_customertransactions", "Sales.CustomerTransactions", required=False),
]

SOURCES_BY_TABLE = {s.table: s for s in SOURCES}


def find_file(directory: Path, source: Source) -> Path | None:
    """Locate a source file case-insensitively (Kaggle uses ``Sales_Customers.csv``)."""
    if directory is None or not directory.exists():
        return None
    wanted = source.filename.lower()
    for candidate in directory.rglob("*.csv"):
        if candidate.name.lower() == wanted and candidate.stat().st_size > 0:
            return candidate
    return None


def resolve_sources(raw_dir: Path, batch_dir: Path | None = None) -> dict[str, Path]:
    """Return {table: path}.  Files in ``batch_dir`` override those in ``raw_dir``."""
    resolved: dict[str, Path] = {}
    for source in SOURCES:
        path = find_file(batch_dir, source) if batch_dir else None
        path = path or find_file(raw_dir, source)
        if path is not None:
            resolved[source.table] = path
    return resolved


def missing_required(resolved: dict[str, Path]) -> list[str]:
    return [s.filename for s in SOURCES if s.required and s.table not in resolved]
