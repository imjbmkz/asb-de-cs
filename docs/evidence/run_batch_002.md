# Pipeline run `20261106T114453_03f591`

## Pipeline run

| run_id | batch_label | status | started_at | finished_at | duration_sec | error_message |
|---|---|---|---|---|---|---|
| 20261106T114453_03f591 | batch_002 | SUCCEEDED | 2026-11-06 11:44:53.911293 | 2026-11-06 11:45:49.990699 | 56.10 |  |

## Orchestrated steps

| step_name | status | duration_sec | message |
|---|---|---|---|
| download_raw_files | SUCCEEDED | 0.00 |  |
| validate_source_files | SUCCEEDED | 0.00 |  |
| prepare_oltp_database | SUCCEEDED | 0.05 |  |
| ingest_csv_to_bronze | SUCCEEDED | 15.16 |  |
| load_oltp_silver | SUCCEEDED | 31.82 |  |
| validate_oltp | SUCCEEDED | 0.31 |  |
| prepare_olap | SUCCEEDED | 2.00 |  |
| load_dimensions | SUCCEEDED | 0.23 |  |
| load_facts | SUCCEEDED | 5.95 |  |
| final_quality_checks | SUCCEEDED | 0.49 |  |
| record_pipeline_result | SUCCEEDED | 0.00 | SUCCEEDED |

## CSV -> bronze ingestion

| table_name | source_file | size_mb | sha256_prefix | rows_loaded | ingested_at |
|---|---|---|---|---|---|
| application_countries | raw/application_countries.csv | 0.03 | 09400bfa9135 | 190 | 2026-11-06 11:44:54.027238 |
| application_stateprovinces | raw/application_stateprovinces.csv | 0.00 | 1269b75c1d58 | 53 | 2026-11-06 11:44:54.034248 |
| application_cities | raw/application_cities.csv | 3.52 | 03a2c418eb61 | 37940 | 2026-11-06 11:44:54.115581 |
| application_people | raw/application_people.csv | 1.54 | 1e6c2e27b770 | 7646 | 2026-11-06 11:44:54.155275 |
| application_deliverymethods | raw/application_deliverymethods.csv | 0.00 | 6dfe618b1d7c | 10 | 2026-11-06 11:44:54.161326 |
| application_paymentmethods | raw/application_paymentmethods.csv | 0.00 | fd17a7ea8d34 | 4 | 2026-11-06 11:44:54.166867 |
| application_transactiontypes | raw/application_transactiontypes.csv | 0.00 | ad44ac2deadb | 13 | 2026-11-06 11:44:54.171887 |
| purchasing_suppliercategories | raw/purchasing_suppliercategories.csv | 0.00 | 5c63e7e1c85b | 9 | 2026-11-06 11:44:54.176782 |
| purchasing_suppliers | raw/purchasing_suppliers.csv | 0.01 | 76c7e537f4b2 | 42 | 2026-11-06 11:44:54.183754 |
| warehouse_colors | raw/warehouse_colors.csv | 0.00 | 7bb3ae0ffc6d | 36 | 2026-11-06 11:44:54.188626 |
| warehouse_packagetypes | raw/warehouse_packagetypes.csv | 0.00 | 396c5a5f86de | 14 | 2026-11-06 11:44:54.193814 |
| warehouse_stockgroups | raw/warehouse_stockgroups.csv | 0.00 | 854955d77686 | 10 | 2026-11-06 11:44:54.198649 |
| warehouse_stockitems | batch_002/warehouse_stockitems.csv | 0.06 | 0c45b6fec944 | 230 | 2026-11-06 11:44:54.207569 |
| warehouse_stockitemstockgroups | raw/warehouse_stockitemstockgroups.csv | 0.01 | a5aa6c21350d | 442 | 2026-11-06 11:44:54.213969 |
| warehouse_stockitemholdings | raw/warehouse_stockitemholdings.csv | 0.01 | 6a7cf5803534 | 227 | 2026-11-06 11:44:54.219831 |
| sales_customercategories | raw/sales_customercategories.csv | 0.00 | 9a2943768a9d | 8 | 2026-11-06 11:44:54.224599 |
| sales_buyinggroups | raw/sales_buyinggroups.csv | 0.00 | 4f941e638a98 | 2 | 2026-11-06 11:44:54.229699 |
| sales_customers | batch_002/sales_customers.csv | 1.10 | 42acecb4afbe | 3788 | 2026-11-06 11:44:54.263142 |
| sales_orders | raw/sales_orders.csv | 115.34 | 91831a5d29a6 | 1068847 | 2026-11-06 11:44:56.635469 |
| sales_orderlines | raw/sales_orderlines.csv | 240.10 | 97907a0b8655 | 2219442 | 2026-11-06 11:44:58.985964 |
| sales_invoices | raw/sales_invoices.csv | 312.15 | 92e2af3501f6 | 583502 | 2026-11-06 11:45:02.665225 |
| sales_invoicelines | raw/sales_invoicelines.csv | 143.68 | cfeb29adac28 | 1280135 | 2026-11-06 11:45:07.196027 |
| sales_customertransactions | raw/sales_customertransactions.csv | 65.23 | a77aaf713c43 | 599367 | 2026-11-06 11:45:09.116223 |

## Bronze -> silver (OLTP) load

| table_name | bronze_rows | exact_duplicates | archived_versions | quarantined_rows | loaded_rows | invalid_casts |
|---|---|---|---|---|---|---|
| application_countries | 190 | 0 | 0 | 0 | 190 | 0 |
| application_stateprovinces | 53 | 0 | 0 | 0 | 53 | 0 |
| application_cities | 37940 | 0 | 0 | 0 | 37940 | 0 |
| application_people | 7646 | 0 | 4517 | 0 | 3129 | 0 |
| application_deliverymethods | 10 | 0 | 0 | 0 | 10 | 0 |
| application_paymentmethods | 4 | 0 | 0 | 0 | 4 | 0 |
| application_transactiontypes | 13 | 0 | 0 | 0 | 13 | 0 |
| purchasing_suppliercategories | 9 | 0 | 0 | 0 | 9 | 0 |
| purchasing_suppliers | 42 | 0 | 28 | 0 | 14 | 0 |
| warehouse_colors | 36 | 0 | 0 | 0 | 36 | 0 |
| warehouse_packagetypes | 14 | 0 | 0 | 0 | 14 | 0 |
| warehouse_stockgroups | 10 | 0 | 0 | 0 | 10 | 0 |
| warehouse_stockitems | 230 | 0 | 3 | 0 | 227 | 0 |
| warehouse_stockitemstockgroups | 442 | 0 | 0 | 0 | 442 | 0 |
| warehouse_stockitemholdings | 227 | 0 | 0 | 0 | 227 | 0 |
| sales_customercategories | 8 | 0 | 0 | 0 | 8 | 0 |
| sales_buyinggroups | 2 | 0 | 0 | 0 | 2 | 0 |
| sales_customers | 3788 | 0 | 2304 | 0 | 1484 | 0 |
| sales_orders | 1068847 | 0 | 0 | 0 | 1068847 | 0 |
| sales_orderlines | 2219442 | 0 | 0 | 43 | 2219399 | 0 |
| sales_invoices | 583502 | 0 | 0 | 41 | 583461 | 0 |
| sales_invoicelines | 1280135 | 0 | 0 | 41 | 1280094 | 0 |
| sales_customertransactions | 599367 | 0 | 0 | 41 | 599326 | 0 |

## Quarantined records by reason

| table_name | reason | rows |
|---|---|---|
| sales_customertransactions | foreign key (invoice_id) not found in sales_invoices | 41 |
| sales_invoicelines | foreign key (invoice_id) not found in sales_invoices | 41 |
| sales_invoices | foreign key (order_id) not found in sales_orders | 41 |
| sales_orderlines | foreign key (order_id) not found in sales_orders | 43 |

## Dimension (SCD) loads

| dimension | scd_type | new_members | new_versions | type1_updates | unchanged |
|---|---|---|---|---|---|
| dim_city | SCD1 | 0 | 0 | 0 | 37940 |
| dim_customer | SCD2 | 0 | 3 | 1 | 1480 |
| dim_employee | SCD1 | 0 | 0 | 0 | 70 |
| dim_stock_item | SCD2 | 0 | 2 | 1 | 224 |
| dim_delivery_method | SCD1 | 0 | 0 | 0 | 10 |

## Fact loads

| fact_table | staged_rows | inserted_rows | updated_rows | deleted_rows | total_rows |
|---|---|---|---|---|---|
| fact_order | 2219399 | 0 | 8455 | 0 | 2219399 |
| fact_sale | 1280094 | 0 | 6657 | 0 | 1280094 |

## Data-quality results

| stage | check_name | severity | failed_rows | result |
|---|---|---|---|---|
| oltp | pk_not_null:sales_customers | critical | 0 | PASS |
| oltp | pk_not_null:warehouse_stockitems | critical | 0 | PASS |
| oltp | pk_not_null:application_people | critical | 0 | PASS |
| oltp | pk_not_null:application_cities | critical | 0 | PASS |
| oltp | pk_not_null:sales_orders | critical | 0 | PASS |
| oltp | pk_not_null:sales_orderlines | critical | 0 | PASS |
| oltp | pk_not_null:sales_invoices | critical | 0 | PASS |
| oltp | pk_not_null:sales_invoicelines | critical | 0 | PASS |
| oltp | unique_key:sales_customers | critical | 0 | PASS |
| oltp | unique_key:warehouse_stockitems | critical | 0 | PASS |
| oltp | unique_key:application_people | critical | 0 | PASS |
| oltp | unique_key:sales_orders | critical | 0 | PASS |
| oltp | unique_key:sales_orderlines | critical | 0 | PASS |
| oltp | unique_key:sales_invoices | critical | 0 | PASS |
| oltp | unique_key:sales_invoicelines | critical | 0 | PASS |
| oltp | fk:customers.bill_to_customer_id | critical | 0 | PASS |
| oltp | fk:orders.backorder_order_id | warning | 0 | PASS |
| oltp | valid:orderlines.quantity>0 | critical | 0 | PASS |
| oltp | valid:orderlines.picked<=quantity | warning | 0 | PASS |
| oltp | valid:invoicelines.quantity | critical | 0 | PASS |
| oltp | valid:invoicelines.amounts | warning | 0 | PASS |
| oltp | valid:prices>=0 | critical | 0 | PASS |
| oltp | valid:transaction_dates_in_range | critical | 0 | PASS |
| oltp | sequence:expected_delivery>=order_date | warning | 0 | PASS |
| oltp | sequence:invoice_date>=order_date | critical | 0 | PASS |
| oltp | sequence:delivery>=invoice_date | warning | 0 | PASS |
| oltp | reconcile:bronze=silver+archive+quarantine+duplicates | critical | 0 | PASS |
| oltp | quarantine:share_within_tolerance | critical | 0 | PASS |
| oltp | quarantine:rows_this_run | warning | 166 | WARN |
| oltp | required_tables_not_empty | critical | 0 | PASS |
| final | unique_surrogate_key:dim_city | critical | 0 | PASS |
| final | not_null_business_key:dim_city | critical | 0 | PASS |
| final | one_current_version:dim_city | critical | 0 | PASS |
| final | valid_range:dim_city | critical | 0 | PASS |
| final | unique_surrogate_key:dim_customer | critical | 0 | PASS |
| final | not_null_business_key:dim_customer | critical | 0 | PASS |
| final | one_current_version:dim_customer | critical | 0 | PASS |
| final | valid_range:dim_customer | critical | 0 | PASS |
| final | no_overlap:dim_customer | critical | 0 | PASS |
| final | no_gaps:dim_customer | critical | 0 | PASS |
| final | current_is_open:dim_customer | critical | 0 | PASS |
| final | no_redundant_versions:dim_customer | critical | 0 | PASS |
| final | unique_surrogate_key:dim_employee | critical | 0 | PASS |
| final | not_null_business_key:dim_employee | critical | 0 | PASS |
| final | one_current_version:dim_employee | critical | 0 | PASS |
| final | valid_range:dim_employee | critical | 0 | PASS |
| final | unique_surrogate_key:dim_stock_item | critical | 0 | PASS |
| final | not_null_business_key:dim_stock_item | critical | 0 | PASS |
| final | one_current_version:dim_stock_item | critical | 0 | PASS |
| final | valid_range:dim_stock_item | critical | 0 | PASS |
| final | no_overlap:dim_stock_item | critical | 0 | PASS |
| final | no_gaps:dim_stock_item | critical | 0 | PASS |
| final | current_is_open:dim_stock_item | critical | 0 | PASS |
| final | no_redundant_versions:dim_stock_item | critical | 0 | PASS |
| final | unique_surrogate_key:dim_delivery_method | critical | 0 | PASS |
| final | not_null_business_key:dim_delivery_method | critical | 0 | PASS |
| final | one_current_version:dim_delivery_method | critical | 0 | PASS |
| final | valid_range:dim_delivery_method | critical | 0 | PASS |
| final | dim_date:fiscal_year_rule | critical | 0 | PASS |
| final | unique_grain:fact_order | critical | 0 | PASS |
| final | unique_grain:fact_sale | critical | 0 | PASS |
| final | completeness:fact_order=stage | critical | 0 | PASS |
| final | completeness:fact_sale=stage | critical | 0 | PASS |
| final | reconcile:fact_sale_amount=oltp | critical | 0 | PASS |
| final | reconcile:fact_order_quantity=oltp | critical | 0 | PASS |
| final | fact_keys_not_null:fact_order | critical | 0 | PASS |
| final | fact_keys_not_null:fact_sale | critical | 0 | PASS |
| final | fact_keys_exist:fact_sale | critical | 0 | PASS |
| final | fact_keys_exist:fact_order | critical | 0 | PASS |
| final | unknown_members:fact_sale | warning | 0 | PASS |
| final | unknown_members:fact_order | warning | 0 | PASS |
| final | scd_point_in_time:fact_sale | critical | 0 | PASS |
| final | scd_point_in_time:fact_order | critical | 0 | PASS |
| final | valid:fact_measures | critical | 0 | PASS |

## Row counts after the run

| layer | table_name | rows |
|---|---|---|
| bronze | application_cities | 37940 |
| bronze | application_countries | 190 |
| bronze | application_deliverymethods | 10 |
| bronze | application_paymentmethods | 4 |
| bronze | application_people | 7646 |
| bronze | application_stateprovinces | 53 |
| bronze | application_transactiontypes | 13 |
| bronze | purchasing_suppliercategories | 9 |
| bronze | purchasing_suppliers | 42 |
| bronze | sales_buyinggroups | 2 |
| bronze | sales_customercategories | 8 |
| bronze | sales_customers | 3788 |
| bronze | sales_customertransactions | 599367 |
| bronze | sales_invoicelines | 1280135 |
| bronze | sales_invoices | 583502 |
| bronze | sales_orderlines | 2219442 |
| bronze | sales_orders | 1068847 |
| bronze | warehouse_colors | 36 |
| bronze | warehouse_packagetypes | 14 |
| bronze | warehouse_stockgroups | 10 |
| bronze | warehouse_stockitemholdings | 227 |
| bronze | warehouse_stockitems | 230 |
| bronze | warehouse_stockitemstockgroups | 442 |
| silver | application_cities | 37940 |
| silver | application_cities_archive | 0 |
| silver | application_countries | 190 |
| silver | application_countries_archive | 0 |
| silver | application_deliverymethods | 10 |
| silver | application_deliverymethods_archive | 0 |
| silver | application_paymentmethods | 4 |
| silver | application_paymentmethods_archive | 0 |
| silver | application_people | 3129 |
| silver | application_people_archive | 4517 |
| silver | application_stateprovinces | 53 |
| silver | application_stateprovinces_archive | 0 |
| silver | application_transactiontypes | 13 |
| silver | application_transactiontypes_archive | 0 |
| silver | purchasing_suppliercategories | 9 |
| silver | purchasing_suppliercategories_archive | 0 |
| silver | purchasing_suppliers | 14 |
| silver | purchasing_suppliers_archive | 28 |
| silver | sales_buyinggroups | 2 |
| silver | sales_buyinggroups_archive | 0 |
| silver | sales_customercategories | 8 |
| silver | sales_customercategories_archive | 0 |
| silver | sales_customers | 1484 |
| silver | sales_customers_archive | 2304 |
| silver | sales_customertransactions | 599326 |
| silver | sales_invoicelines | 1280094 |
| silver | sales_invoices | 583461 |
| silver | sales_orderlines | 2219399 |
| silver | sales_orders | 1068847 |
| silver | warehouse_colors | 36 |
| silver | warehouse_colors_archive | 0 |
| silver | warehouse_packagetypes | 14 |
| silver | warehouse_packagetypes_archive | 0 |
| silver | warehouse_stockgroups | 10 |
| silver | warehouse_stockgroups_archive | 0 |
| silver | warehouse_stockitemholdings | 227 |
| silver | warehouse_stockitems | 227 |
| silver | warehouse_stockitems_archive | 3 |
| silver | warehouse_stockitemstockgroups | 442 |
| stage | city | 37940 |
| stage | customer | 1484 |
| stage | delivery_method | 10 |
| stage | employee | 70 |
| stage | order_line | 2219399 |
| stage | sale | 1280094 |
| stage | stock_item | 227 |
| gold | dim_city | 37941 |
| gold | dim_customer | 1488 |
| gold | dim_date | 1827 |
| gold | dim_delivery_method | 11 |
| gold | dim_employee | 71 |
| gold | dim_stock_item | 230 |
| gold | fact_order | 2219399 |
| gold | fact_sale | 1280094 |
