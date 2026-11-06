-- =============================================================================
-- GOLD = OLAP star schema.  Persistent across runs (never dropped) because it
-- holds the SCD history.  Every statement is idempotent.
--
-- Conventions
--   *_key            surrogate key (max + row_number, deterministic); 0 = "Unknown" member
--   <entity>_id      business / natural key from the OLTP source
--   valid_from/to    half-open validity interval [valid_from, valid_to)
--   is_current       TRUE for the open version of a business key
--   _t2_hash/_t1_hash  hashes of the type-2 / type-1 attribute sets (change detection)
-- =============================================================================
CREATE SCHEMA IF NOT EXISTS gold;


-- ----------------------------------------------------------------- dim_date
CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key                INTEGER PRIMARY KEY,      -- yyyymmdd
    date                    DATE NOT NULL UNIQUE,
    day_of_month            INTEGER NOT NULL,
    day_name                VARCHAR NOT NULL,
    day_of_week             INTEGER NOT NULL,         -- ISO: 1 = Monday
    is_weekend              BOOLEAN NOT NULL,
    week_of_year            INTEGER NOT NULL,         -- ISO week
    calendar_month          INTEGER NOT NULL,
    calendar_month_name     VARCHAR NOT NULL,
    calendar_month_label    VARCHAR NOT NULL,         -- e.g. 2016-07
    calendar_quarter        INTEGER NOT NULL,
    calendar_year           INTEGER NOT NULL,
    fiscal_month            INTEGER NOT NULL,         -- 1 = November
    fiscal_quarter          INTEGER NOT NULL,
    fiscal_year             INTEGER NOT NULL,         -- FY2016 = 2015-11-01 .. 2016-10-31
    fiscal_month_label      VARCHAR NOT NULL,         -- e.g. FY2016-M09
    fiscal_year_label       VARCHAR NOT NULL          -- e.g. FY2016
);

-- ----------------------------------------------------------------- dim_city  (SCD1)
CREATE TABLE IF NOT EXISTS gold.dim_city (
    city_key                    BIGINT PRIMARY KEY,
    city_id                     INTEGER NOT NULL,
    city                        VARCHAR,
    state_province_code         VARCHAR,
    state_province              VARCHAR,
    sales_territory             VARCHAR,
    country                     VARCHAR,
    continent                   VARCHAR,
    region                      VARCHAR,
    subregion                   VARCHAR,
    latitude                    DOUBLE,
    longitude                   DOUBLE,
    latest_recorded_population  BIGINT,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    is_current                  BOOLEAN NOT NULL,
    _t2_hash                    VARCHAR,
    _t1_hash                    VARCHAR,
    _inserted_run_id            VARCHAR,
    _updated_run_id             VARCHAR
);

-- ----------------------------------------------------------------- dim_customer  (SCD2)
CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_key                BIGINT PRIMARY KEY,
    customer_id                 INTEGER NOT NULL,
    -- type 2 (history tracked)
    customer_category           VARCHAR,
    buying_group                VARCHAR,
    bill_to_customer_id         INTEGER,
    delivery_city_id            INTEGER,
    delivery_city               VARCHAR,
    delivery_state_province     VARCHAR,
    delivery_postal_code        VARCHAR,
    credit_limit                DECIMAL(18, 2),
    payment_days                INTEGER,
    standard_discount_percentage DECIMAL(18, 3),
    -- type 1 (overwritten)
    customer_name               VARCHAR,
    bill_to_customer_name       VARCHAR,
    primary_contact             VARCHAR,
    delivery_method             VARCHAR,
    phone_number                VARCHAR,
    website_url                 VARCHAR,
    account_opened_date         DATE,
    is_on_credit_hold           BOOLEAN,
    is_statement_sent           BOOLEAN,
    -- SCD metadata
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    is_current                  BOOLEAN NOT NULL,
    _t2_hash                    VARCHAR,
    _t1_hash                    VARCHAR,
    _inserted_run_id            VARCHAR,
    _updated_run_id             VARCHAR
);

-- ----------------------------------------------------------------- dim_employee  (SCD1)
CREATE TABLE IF NOT EXISTS gold.dim_employee (
    employee_key                BIGINT PRIMARY KEY,
    employee_id                 INTEGER NOT NULL,     -- Application.People.PersonID
    full_name                   VARCHAR,
    preferred_name              VARCHAR,
    is_salesperson              BOOLEAN,
    email_address               VARCHAR,
    phone_number                VARCHAR,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    is_current                  BOOLEAN NOT NULL,
    _t2_hash                    VARCHAR,
    _t1_hash                    VARCHAR,
    _inserted_run_id            VARCHAR,
    _updated_run_id             VARCHAR
);

-- ----------------------------------------------------------------- dim_stock_item  (SCD2)
CREATE TABLE IF NOT EXISTS gold.dim_stock_item (
    stock_item_key              BIGINT PRIMARY KEY,
    stock_item_id               INTEGER NOT NULL,
    -- type 2 (history tracked)
    brand                       VARCHAR,
    size                        VARCHAR,
    color                       VARCHAR,
    selling_package             VARCHAR,
    buying_package              VARCHAR,
    supplier_id                 INTEGER,
    supplier_name               VARCHAR,
    is_chiller_stock            BOOLEAN,
    tax_rate                    DECIMAL(18, 3),
    unit_price                  DECIMAL(18, 2),
    recommended_retail_price    DECIMAL(18, 2),
    -- type 1 (overwritten)
    stock_item_name             VARCHAR,
    primary_stock_group         VARCHAR,
    stock_groups                VARCHAR,
    barcode                     VARCHAR,
    lead_time_days              INTEGER,
    quantity_per_outer          INTEGER,
    typical_weight_per_unit     DECIMAL(18, 3),
    -- SCD metadata
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    is_current                  BOOLEAN NOT NULL,
    _t2_hash                    VARCHAR,
    _t1_hash                    VARCHAR,
    _inserted_run_id            VARCHAR,
    _updated_run_id             VARCHAR
);

-- ----------------------------------------------------------------- dim_delivery_method  (SCD1)
CREATE TABLE IF NOT EXISTS gold.dim_delivery_method (
    delivery_method_key         BIGINT PRIMARY KEY,
    delivery_method_id          INTEGER NOT NULL,
    delivery_method             VARCHAR,
    valid_from                  TIMESTAMP NOT NULL,
    valid_to                    TIMESTAMP NOT NULL,
    is_current                  BOOLEAN NOT NULL,
    _t2_hash                    VARCHAR,
    _t1_hash                    VARCHAR,
    _inserted_run_id            VARCHAR,
    _updated_run_id             VARCHAR
);

-- ----------------------------------------------------------------- Unknown members (key 0)
INSERT INTO gold.dim_city (city_key, city_id, city, state_province, sales_territory, country, valid_from, valid_to, is_current)
SELECT 0, -1, 'Unknown', 'Unknown', 'Unknown', 'Unknown', TIMESTAMP '1900-01-01', TIMESTAMP '9999-12-31', TRUE
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_city WHERE city_key = 0);

INSERT INTO gold.dim_customer (customer_key, customer_id, customer_name, customer_category, buying_group, valid_from, valid_to, is_current)
SELECT 0, -1, 'Unknown', 'Unknown', 'Unknown', TIMESTAMP '1900-01-01', TIMESTAMP '9999-12-31', TRUE
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_customer WHERE customer_key = 0);

INSERT INTO gold.dim_employee (employee_key, employee_id, full_name, preferred_name, valid_from, valid_to, is_current)
SELECT 0, -1, 'Unknown', 'Unknown', TIMESTAMP '1900-01-01', TIMESTAMP '9999-12-31', TRUE
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_employee WHERE employee_key = 0);

INSERT INTO gold.dim_stock_item (stock_item_key, stock_item_id, stock_item_name, brand, primary_stock_group, valid_from, valid_to, is_current)
SELECT 0, -1, 'Unknown', 'Unknown', 'Unknown', TIMESTAMP '1900-01-01', TIMESTAMP '9999-12-31', TRUE
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_stock_item WHERE stock_item_key = 0);

INSERT INTO gold.dim_delivery_method (delivery_method_key, delivery_method_id, delivery_method, valid_from, valid_to, is_current)
SELECT 0, -1, 'Unknown', TIMESTAMP '1900-01-01', TIMESTAMP '9999-12-31', TRUE
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_delivery_method WHERE delivery_method_key = 0);

INSERT INTO gold.dim_date
SELECT -1, DATE '1900-01-01', 0, 'Unknown', 0, FALSE, 0, 0, 'Unknown', 'Unknown', 0, 0, 0, 0, 0, 'Unknown', 'Unknown'
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_date WHERE date_key = -1);

-- ----------------------------------------------------------------- fact_order
-- Grain: one row per customer order line (Sales.OrderLines.OrderLineID).
CREATE TABLE IF NOT EXISTS gold.fact_order (
    order_line_id               INTEGER PRIMARY KEY,   -- degenerate natural key of the grain
    order_id                    INTEGER NOT NULL,      -- degenerate dimension
    backorder_order_id          INTEGER,
    order_date_key              INTEGER NOT NULL,
    expected_delivery_date_key  INTEGER NOT NULL,
    picked_date_key             INTEGER,               -- NULL while not yet picked
    customer_key                BIGINT NOT NULL,
    city_key                    BIGINT NOT NULL,
    salesperson_key             BIGINT NOT NULL,
    picker_key                  BIGINT NOT NULL,
    stock_item_key              BIGINT NOT NULL,
    description                 VARCHAR,
    package                     VARCHAR,
    customer_purchase_order_number VARCHAR,
    is_undersupply_backordered  BOOLEAN NOT NULL,
    quantity                    INTEGER NOT NULL,
    picked_quantity             INTEGER NOT NULL,
    unit_price                  DECIMAL(18, 2),
    tax_rate                    DECIMAL(18, 3),
    total_excluding_tax         DECIMAL(18, 2),
    tax_amount                  DECIMAL(18, 2),
    total_including_tax         DECIMAL(18, 2),
    _row_hash                   VARCHAR NOT NULL,
    _run_id                     VARCHAR NOT NULL,
    _loaded_at                  TIMESTAMP NOT NULL
);

-- ----------------------------------------------------------------- fact_sale
-- Grain: one row per customer invoice line (Sales.InvoiceLines.InvoiceLineID).
CREATE TABLE IF NOT EXISTS gold.fact_sale (
    invoice_line_id             INTEGER PRIMARY KEY,   -- degenerate natural key of the grain
    invoice_id                  INTEGER NOT NULL,      -- degenerate dimension
    order_id                    INTEGER,
    invoice_date_key            INTEGER NOT NULL,
    order_date_key              INTEGER,
    delivery_date_key           INTEGER,               -- NULL when not (yet) delivered
    customer_key                BIGINT NOT NULL,
    bill_to_customer_key        BIGINT NOT NULL,
    city_key                    BIGINT NOT NULL,
    salesperson_key             BIGINT NOT NULL,
    stock_item_key              BIGINT NOT NULL,
    delivery_method_key         BIGINT NOT NULL,
    description                 VARCHAR,
    package                     VARCHAR,
    is_credit_note              BOOLEAN NOT NULL,
    quantity                    INTEGER NOT NULL,
    unit_price                  DECIMAL(18, 2),
    tax_rate                    DECIMAL(18, 3),
    total_excluding_tax         DECIMAL(18, 2) NOT NULL,
    tax_amount                  DECIMAL(18, 2) NOT NULL,
    total_including_tax         DECIMAL(18, 2) NOT NULL,
    profit                      DECIMAL(18, 2) NOT NULL,
    days_order_to_invoice       INTEGER,
    days_invoice_to_delivery    INTEGER,
    _row_hash                   VARCHAR NOT NULL,
    _run_id                     VARCHAR NOT NULL,
    _loaded_at                  TIMESTAMP NOT NULL
);
