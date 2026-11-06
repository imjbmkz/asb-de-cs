-- =============================================================================
-- SILVER = OLTP database (normalized, typed, constraint-enforced)
--
-- Mirrors the WideWorldImporters OLTP schemas (Application, Purchasing,
-- Warehouse, Sales).  Table name = <source schema>_<source table>; column names
-- are the source names converted to snake_case (CustomerID -> customer_id).
--
-- * PRIMARY KEY / UNIQUE / NOT NULL / CHECK / FOREIGN KEY constraints are
--   declared here and enforced by DuckDB on insert.  The loader (silver.py)
--   reads these constraints from the catalog and routes rows that would violate
--   them to quarantine.rejected_records instead of failing the whole load.
-- * WWI tables are system-versioned temporal tables.  The export contains both
--   current and historical versions; the current version is loaded here and the
--   other versions go to <table>_archive (created by the loader), like WWI's
--   *_Archive tables.
-- * LastEditedBy -> People foreign keys and self references (BillToCustomerID)
--   are intentionally not declared (audit columns / validated as DQ checks).
--
-- The whole schema is rebuilt on every run (full refresh from bronze), which
-- keeps the OLTP layer idempotent.
-- =============================================================================
DROP SCHEMA IF EXISTS silver CASCADE;
CREATE SCHEMA silver;

-- ----------------------------------------------------------------- Application
CREATE TABLE silver.application_countries (
    country_id                  INTEGER PRIMARY KEY,
    country_name                VARCHAR NOT NULL,
    formal_name                 VARCHAR NOT NULL,
    iso_alpha3_code             VARCHAR,
    iso_numeric_code            INTEGER,
    country_type                VARCHAR,
    latest_recorded_population  BIGINT,
    continent                   VARCHAR NOT NULL,
    region                      VARCHAR NOT NULL,
    subregion                   VARCHAR NOT NULL,
    border                      VARCHAR,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    UNIQUE (country_name)
);

CREATE TABLE silver.application_stateprovinces (
    state_province_id           INTEGER PRIMARY KEY,
    state_province_code         VARCHAR NOT NULL,
    state_province_name         VARCHAR NOT NULL,
    country_id                  INTEGER NOT NULL REFERENCES silver.application_countries (country_id),
    sales_territory             VARCHAR NOT NULL,
    border                      VARCHAR,
    latest_recorded_population  BIGINT,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.application_cities (
    city_id                     INTEGER PRIMARY KEY,
    city_name                   VARCHAR NOT NULL,
    state_province_id           INTEGER NOT NULL REFERENCES silver.application_stateprovinces (state_province_id),
    location                    VARCHAR,           -- WKT point "POINT (lon lat)"
    latest_recorded_population  BIGINT,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.application_people (
    person_id                   INTEGER PRIMARY KEY,
    full_name                   VARCHAR NOT NULL,
    preferred_name              VARCHAR NOT NULL,
    search_name                 VARCHAR NOT NULL,
    is_permitted_to_logon       BOOLEAN NOT NULL,
    logon_name                  VARCHAR,
    is_external_logon_provider  BOOLEAN NOT NULL,
    hashed_password             VARCHAR,
    is_system_user              BOOLEAN NOT NULL,
    is_employee                 BOOLEAN NOT NULL,
    is_salesperson              BOOLEAN NOT NULL,
    user_preferences            VARCHAR,
    phone_number                VARCHAR,
    fax_number                  VARCHAR,
    email_address               VARCHAR,
    photo                       VARCHAR,
    custom_fields               VARCHAR,
    other_languages             VARCHAR,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.application_deliverymethods (
    delivery_method_id          INTEGER PRIMARY KEY,
    delivery_method_name        VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.application_paymentmethods (
    payment_method_id           INTEGER PRIMARY KEY,
    payment_method_name         VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.application_transactiontypes (
    transaction_type_id         INTEGER PRIMARY KEY,
    transaction_type_name       VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

-- ------------------------------------------------------------------ Purchasing
CREATE TABLE silver.purchasing_suppliercategories (
    supplier_category_id        INTEGER PRIMARY KEY,
    supplier_category_name      VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.purchasing_suppliers (
    supplier_id                 INTEGER PRIMARY KEY,
    supplier_name               VARCHAR NOT NULL,
    supplier_category_id        INTEGER NOT NULL REFERENCES silver.purchasing_suppliercategories (supplier_category_id),
    primary_contact_person_id   INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    alternate_contact_person_id INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    delivery_method_id          INTEGER REFERENCES silver.application_deliverymethods (delivery_method_id),
    delivery_city_id            INTEGER NOT NULL REFERENCES silver.application_cities (city_id),
    postal_city_id              INTEGER NOT NULL REFERENCES silver.application_cities (city_id),
    supplier_reference          VARCHAR,
    bank_account_name           VARCHAR,
    bank_account_branch         VARCHAR,
    bank_account_code           VARCHAR,
    bank_account_number         VARCHAR,
    bank_international_code     VARCHAR,
    payment_days                INTEGER NOT NULL,
    internal_comments           VARCHAR,
    phone_number                VARCHAR NOT NULL,
    fax_number                  VARCHAR NOT NULL,
    website_url                 VARCHAR NOT NULL,
    delivery_address_line1      VARCHAR,            -- NOT NULL in WWI, blank for some suppliers in the export
    delivery_address_line2      VARCHAR,
    delivery_postal_code        VARCHAR NOT NULL,
    delivery_location           VARCHAR,
    postal_address_line1        VARCHAR NOT NULL,
    postal_address_line2        VARCHAR,
    postal_postal_code          VARCHAR NOT NULL,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

-- ------------------------------------------------------------------- Warehouse
CREATE TABLE silver.warehouse_colors (
    color_id                    INTEGER PRIMARY KEY,
    color_name                  VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.warehouse_packagetypes (
    package_type_id             INTEGER PRIMARY KEY,
    package_type_name           VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.warehouse_stockgroups (
    stock_group_id              INTEGER PRIMARY KEY,
    stock_group_name            VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.warehouse_stockitems (
    stock_item_id               INTEGER PRIMARY KEY,
    stock_item_name             VARCHAR NOT NULL,
    supplier_id                 INTEGER NOT NULL REFERENCES silver.purchasing_suppliers (supplier_id),
    color_id                    INTEGER REFERENCES silver.warehouse_colors (color_id),
    unit_package_id             INTEGER NOT NULL REFERENCES silver.warehouse_packagetypes (package_type_id),
    outer_package_id            INTEGER NOT NULL REFERENCES silver.warehouse_packagetypes (package_type_id),
    brand                       VARCHAR,
    size                        VARCHAR,
    lead_time_days              INTEGER NOT NULL,
    quantity_per_outer          INTEGER NOT NULL,
    is_chiller_stock            BOOLEAN NOT NULL,
    barcode                     VARCHAR,
    tax_rate                    DECIMAL(18, 3) NOT NULL,
    unit_price                  DECIMAL(18, 2) NOT NULL,
    recommended_retail_price    DECIMAL(18, 2),
    typical_weight_per_unit     DECIMAL(18, 3) NOT NULL,
    marketing_comments          VARCHAR,
    internal_comments           VARCHAR,
    photo                       VARCHAR,
    custom_fields               VARCHAR,
    tags                        VARCHAR,
    search_details              VARCHAR NOT NULL,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    CHECK (unit_price >= 0),
    CHECK (tax_rate >= 0)
);

CREATE TABLE silver.warehouse_stockitemstockgroups (
    stock_item_stock_group_id   INTEGER PRIMARY KEY,
    stock_item_id               INTEGER NOT NULL REFERENCES silver.warehouse_stockitems (stock_item_id),
    stock_group_id              INTEGER NOT NULL REFERENCES silver.warehouse_stockgroups (stock_group_id),
    last_edited_by              INTEGER NOT NULL,
    last_edited_when            TIMESTAMP NOT NULL,
    UNIQUE (stock_item_id, stock_group_id)
);

CREATE TABLE silver.warehouse_stockitemholdings (
    stock_item_id               INTEGER PRIMARY KEY REFERENCES silver.warehouse_stockitems (stock_item_id),
    quantity_on_hand            INTEGER NOT NULL,
    bin_location                VARCHAR NOT NULL,
    last_stocktake_quantity     INTEGER NOT NULL,
    last_cost_price             DECIMAL(18, 2) NOT NULL,
    reorder_level               INTEGER NOT NULL,
    target_stock_level          INTEGER NOT NULL,
    last_edited_by              INTEGER NOT NULL,
    last_edited_when            TIMESTAMP NOT NULL
);

-- ----------------------------------------------------------------------- Sales
CREATE TABLE silver.sales_customercategories (
    customer_category_id        INTEGER PRIMARY KEY,
    customer_category_name      VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.sales_buyinggroups (
    buying_group_id             INTEGER PRIMARY KEY,
    buying_group_name           VARCHAR NOT NULL UNIQUE,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL
);

CREATE TABLE silver.sales_customers (
    customer_id                 INTEGER PRIMARY KEY,
    customer_name               VARCHAR NOT NULL,
    bill_to_customer_id         INTEGER NOT NULL,   -- self reference, validated as a DQ check
    customer_category_id        INTEGER NOT NULL REFERENCES silver.sales_customercategories (customer_category_id),
    buying_group_id             INTEGER REFERENCES silver.sales_buyinggroups (buying_group_id),
    primary_contact_person_id   INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    alternate_contact_person_id INTEGER REFERENCES silver.application_people (person_id),
    delivery_method_id          INTEGER NOT NULL REFERENCES silver.application_deliverymethods (delivery_method_id),
    delivery_city_id            INTEGER NOT NULL REFERENCES silver.application_cities (city_id),
    postal_city_id              INTEGER NOT NULL REFERENCES silver.application_cities (city_id),
    credit_limit                DECIMAL(18, 2),
    account_opened_date         DATE NOT NULL,
    standard_discount_percentage DECIMAL(18, 3) NOT NULL,
    is_statement_sent           BOOLEAN NOT NULL,
    is_on_credit_hold           BOOLEAN NOT NULL,
    payment_days                INTEGER NOT NULL,
    phone_number                VARCHAR NOT NULL,
    fax_number                  VARCHAR NOT NULL,
    delivery_run                VARCHAR,
    run_position                VARCHAR,
    website_url                 VARCHAR NOT NULL,
    delivery_address_line1      VARCHAR NOT NULL,
    delivery_address_line2      VARCHAR,
    delivery_postal_code        VARCHAR NOT NULL,
    delivery_location           VARCHAR,
    postal_address_line1        VARCHAR NOT NULL,
    postal_address_line2        VARCHAR,
    postal_postal_code          VARCHAR NOT NULL,
    last_edited_by              INTEGER NOT NULL,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    CHECK (credit_limit IS NULL OR credit_limit >= 0),
    CHECK (payment_days >= 0)
);

CREATE TABLE silver.sales_orders (
    order_id                    INTEGER PRIMARY KEY,
    customer_id                 INTEGER NOT NULL REFERENCES silver.sales_customers (customer_id),
    salesperson_person_id       INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    picked_by_person_id         INTEGER REFERENCES silver.application_people (person_id),
    contact_person_id           INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    backorder_order_id          INTEGER,            -- self reference (may point to a later order)
    order_date                  DATE NOT NULL,
    expected_delivery_date      DATE NOT NULL,
    customer_purchase_order_number VARCHAR,
    is_undersupply_backordered  BOOLEAN NOT NULL,
    comments                    VARCHAR,
    delivery_instructions       VARCHAR,
    internal_comments           VARCHAR,
    picking_completed_when      TIMESTAMP,
    last_edited_by              INTEGER NOT NULL,
    last_edited_when            TIMESTAMP NOT NULL
);

CREATE TABLE silver.sales_orderlines (
    order_line_id               INTEGER PRIMARY KEY,
    order_id                    INTEGER NOT NULL REFERENCES silver.sales_orders (order_id),
    stock_item_id               INTEGER NOT NULL REFERENCES silver.warehouse_stockitems (stock_item_id),
    description                 VARCHAR NOT NULL,
    package_type_id             INTEGER NOT NULL REFERENCES silver.warehouse_packagetypes (package_type_id),
    quantity                    INTEGER NOT NULL,
    unit_price                  DECIMAL(18, 2),
    tax_rate                    DECIMAL(18, 3) NOT NULL,
    picked_quantity             INTEGER NOT NULL,
    picking_completed_when      TIMESTAMP,
    last_edited_by              INTEGER NOT NULL,
    last_edited_when            TIMESTAMP NOT NULL,
    CHECK (quantity > 0),
    CHECK (picked_quantity >= 0),
    CHECK (unit_price IS NULL OR unit_price >= 0),
    CHECK (tax_rate >= 0)
);

CREATE TABLE silver.sales_invoices (
    invoice_id                  INTEGER PRIMARY KEY,
    customer_id                 INTEGER NOT NULL REFERENCES silver.sales_customers (customer_id),
    bill_to_customer_id         INTEGER NOT NULL REFERENCES silver.sales_customers (customer_id),
    order_id                    INTEGER REFERENCES silver.sales_orders (order_id),
    delivery_method_id          INTEGER NOT NULL REFERENCES silver.application_deliverymethods (delivery_method_id),
    contact_person_id           INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    accounts_person_id          INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    salesperson_person_id       INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    packed_by_person_id         INTEGER NOT NULL REFERENCES silver.application_people (person_id),
    invoice_date                DATE NOT NULL,
    customer_purchase_order_number VARCHAR,
    is_credit_note              BOOLEAN NOT NULL,
    credit_note_reason          VARCHAR,
    comments                    VARCHAR,
    delivery_instructions       VARCHAR,
    internal_comments           VARCHAR,
    total_dry_items             INTEGER NOT NULL,
    total_chiller_items         INTEGER NOT NULL,
    delivery_run                VARCHAR,
    run_position                VARCHAR,
    returned_delivery_data      VARCHAR,           -- JSON document
    confirmed_delivery_time     TIMESTAMP,
    confirmed_received_by       VARCHAR,
    last_edited_by              INTEGER NOT NULL,
    last_edited_when            TIMESTAMP NOT NULL,
    CHECK (total_dry_items >= 0),
    CHECK (total_chiller_items >= 0)
);

CREATE TABLE silver.sales_invoicelines (
    invoice_line_id             INTEGER PRIMARY KEY,
    invoice_id                  INTEGER NOT NULL REFERENCES silver.sales_invoices (invoice_id),
    stock_item_id               INTEGER NOT NULL REFERENCES silver.warehouse_stockitems (stock_item_id),
    description                 VARCHAR NOT NULL,
    package_type_id             INTEGER NOT NULL REFERENCES silver.warehouse_packagetypes (package_type_id),
    quantity                    INTEGER NOT NULL,
    unit_price                  DECIMAL(18, 2),
    tax_rate                    DECIMAL(18, 3) NOT NULL,
    tax_amount                  DECIMAL(18, 2) NOT NULL,
    line_profit                 DECIMAL(18, 2) NOT NULL,
    extended_price              DECIMAL(18, 2) NOT NULL,
    last_edited_by              INTEGER NOT NULL,
    last_edited_when            TIMESTAMP NOT NULL,
    CHECK (unit_price IS NULL OR unit_price >= 0),
    CHECK (tax_rate >= 0)
);

CREATE TABLE silver.sales_customertransactions (
    customer_transaction_id     INTEGER PRIMARY KEY,
    customer_id                 INTEGER NOT NULL REFERENCES silver.sales_customers (customer_id),
    transaction_type_id         INTEGER NOT NULL REFERENCES silver.application_transactiontypes (transaction_type_id),
    invoice_id                  INTEGER REFERENCES silver.sales_invoices (invoice_id),
    payment_method_id           INTEGER REFERENCES silver.application_paymentmethods (payment_method_id),
    transaction_date            DATE NOT NULL,
    amount_excluding_tax        DECIMAL(18, 2) NOT NULL,
    tax_amount                  DECIMAL(18, 2) NOT NULL,
    transaction_amount          DECIMAL(18, 2) NOT NULL,
    outstanding_balance         DECIMAL(18, 2) NOT NULL,
    finalization_date           DATE,
    is_finalized                BOOLEAN,
    last_edited_by              INTEGER NOT NULL,
    last_edited_when            TIMESTAMP NOT NULL
);
