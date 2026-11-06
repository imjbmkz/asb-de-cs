"""Wide World Importers end-to-end data pipeline built on DuckDB.

Layers (medallion):
    raw      CSV files exactly as downloaded (data/raw), never modified
    bronze   1:1 copy of every CSV as VARCHAR + ingestion metadata ("staging")
    silver   typed, de-duplicated, constraint-enforced OLTP model
    stage    OLAP staging tables shaped for the dimensional model
    gold     star schema: SCD2/SCD1 dimensions and fact tables
"""

__version__ = "1.0.0"
