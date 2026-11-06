-- =============================================================================
-- STAGE = OLAP staging tables.  Built from the SILVER (OLTP) layer only - never
-- from the CSV files.  Joins, cleans, derives and reshapes the normalized OLTP
-- data into one flat row per dimension member / fact grain.  Rebuilt every run.
-- =============================================================================
DROP SCHEMA IF EXISTS stage CASCADE;
CREATE SCHEMA stage;

-- ------------------------------------------------------------------ city
CREATE TABLE stage.city AS
SELECT
    c.city_id,
    c.city_name                                                            AS city,
    sp.state_province_code,
    sp.state_province_name                                                 AS state_province,
    sp.sales_territory,
    co.country_name                                                        AS country,
    co.continent,
    co.region,
    co.subregion,
    TRY_CAST(regexp_extract(c.location, 'POINT \(([-0-9.]+) ([-0-9.]+)\)', 2) AS DOUBLE) AS latitude,
    TRY_CAST(regexp_extract(c.location, 'POINT \(([-0-9.]+) ([-0-9.]+)\)', 1) AS DOUBLE) AS longitude,
    c.latest_recorded_population,
    c.valid_from                                                           AS change_ts
FROM silver.application_cities c
JOIN silver.application_stateprovinces sp ON sp.state_province_id = c.state_province_id
JOIN silver.application_countries co      ON co.country_id = sp.country_id;

-- ------------------------------------------------------------------ customer
CREATE TABLE stage.customer AS
SELECT
    c.customer_id,
    cc.customer_category_name                                              AS customer_category,
    coalesce(bg.buying_group_name, 'N/A')                                  AS buying_group,
    c.bill_to_customer_id,
    c.delivery_city_id,
    ci.city_name                                                           AS delivery_city,
    sp.state_province_name                                                 AS delivery_state_province,
    c.delivery_postal_code,
    c.credit_limit,
    c.payment_days,
    c.standard_discount_percentage,
    c.customer_name,
    bt.customer_name                                                       AS bill_to_customer_name,
    pc.full_name                                                           AS primary_contact,
    dm.delivery_method_name                                                AS delivery_method,
    c.phone_number,
    c.website_url,
    c.account_opened_date,
    c.is_on_credit_hold,
    c.is_statement_sent,
    c.valid_from                                                           AS change_ts
FROM silver.sales_customers c
JOIN silver.sales_customercategories cc        ON cc.customer_category_id = c.customer_category_id
LEFT JOIN silver.sales_buyinggroups bg         ON bg.buying_group_id = c.buying_group_id
LEFT JOIN silver.sales_customers bt            ON bt.customer_id = c.bill_to_customer_id
LEFT JOIN silver.application_people pc         ON pc.person_id = c.primary_contact_person_id
LEFT JOIN silver.application_deliverymethods dm ON dm.delivery_method_id = c.delivery_method_id
LEFT JOIN silver.application_cities ci         ON ci.city_id = c.delivery_city_id
LEFT JOIN silver.application_stateprovinces sp ON sp.state_province_id = ci.state_province_id;

-- ------------------------------------------------------------------ employee
CREATE TABLE stage.employee AS
SELECT
    p.person_id                                                            AS employee_id,
    p.full_name,
    p.preferred_name,
    p.is_salesperson,
    p.email_address,
    p.phone_number,
    p.valid_from                                                           AS change_ts
FROM silver.application_people p
WHERE p.is_employee;

-- ------------------------------------------------------------------ stock item
CREATE TABLE stage.stock_item AS
WITH groups AS (
    SELECT sisg.stock_item_id, sg.stock_group_id, sg.stock_group_name,
           count(*) OVER (PARTITION BY sg.stock_group_id) AS group_size
    FROM silver.warehouse_stockitemstockgroups sisg
    JOIN silver.warehouse_stockgroups sg ON sg.stock_group_id = sisg.stock_group_id
),
item_groups AS (
    SELECT
        stock_item_id,
        -- "Primary" category = the most specific group (fewest member items).
        arg_min(stock_group_name, group_size * 1000 + stock_group_id)      AS primary_stock_group,
        string_agg(stock_group_name, ', ' ORDER BY stock_group_name)       AS stock_groups
    FROM groups
    GROUP BY stock_item_id
)
SELECT
    si.stock_item_id,
    coalesce(si.brand, 'N/A')                                              AS brand,
    coalesce(si.size, 'N/A')                                               AS size,
    coalesce(col.color_name, 'N/A')                                        AS color,
    up.package_type_name                                                   AS selling_package,
    op.package_type_name                                                   AS buying_package,
    si.supplier_id,
    s.supplier_name,
    si.is_chiller_stock,
    si.tax_rate,
    si.unit_price,
    si.recommended_retail_price,
    si.stock_item_name,
    coalesce(ig.primary_stock_group, 'Unassigned')                         AS primary_stock_group,
    coalesce(ig.stock_groups, 'Unassigned')                                AS stock_groups,
    si.barcode,
    si.lead_time_days,
    si.quantity_per_outer,
    si.typical_weight_per_unit,
    si.valid_from                                                          AS change_ts
FROM silver.warehouse_stockitems si
LEFT JOIN silver.warehouse_colors col        ON col.color_id = si.color_id
LEFT JOIN silver.warehouse_packagetypes up   ON up.package_type_id = si.unit_package_id
LEFT JOIN silver.warehouse_packagetypes op   ON op.package_type_id = si.outer_package_id
LEFT JOIN silver.purchasing_suppliers s      ON s.supplier_id = si.supplier_id
LEFT JOIN item_groups ig                     ON ig.stock_item_id = si.stock_item_id;

-- ------------------------------------------------------------------ delivery method
CREATE TABLE stage.delivery_method AS
SELECT delivery_method_id, delivery_method_name AS delivery_method, valid_from AS change_ts
FROM silver.application_deliverymethods;

-- ------------------------------------------------------------------ order lines (fact_order source)
CREATE TABLE stage.order_line AS
SELECT
    ol.order_line_id,
    o.order_id,
    o.backorder_order_id,
    o.order_date,
    o.expected_delivery_date,
    CAST(ol.picking_completed_when AS DATE)                                AS picked_date,
    o.customer_id,
    o.salesperson_person_id,
    o.picked_by_person_id,
    ol.stock_item_id,
    ol.description,
    pt.package_type_name                                                   AS package,
    o.customer_purchase_order_number,
    o.is_undersupply_backordered,
    ol.quantity,
    ol.picked_quantity,
    ol.unit_price,
    ol.tax_rate,
    CAST(ol.quantity * ol.unit_price AS DECIMAL(18, 2))                    AS total_excluding_tax,
    CAST(round(ol.quantity * ol.unit_price * ol.tax_rate / 100, 2) AS DECIMAL(18, 2)) AS tax_amount
FROM silver.sales_orderlines ol
JOIN silver.sales_orders o                ON o.order_id = ol.order_id
LEFT JOIN silver.warehouse_packagetypes pt ON pt.package_type_id = ol.package_type_id;

-- ------------------------------------------------------------------ invoice lines (fact_sale source)
CREATE TABLE stage.sale AS
SELECT
    il.invoice_line_id,
    i.invoice_id,
    i.order_id,
    i.invoice_date,
    o.order_date,
    CAST(i.confirmed_delivery_time AS DATE)                                AS delivery_date,
    i.customer_id,
    i.bill_to_customer_id,
    i.salesperson_person_id,
    il.stock_item_id,
    i.delivery_method_id,
    il.description,
    pt.package_type_name                                                   AS package,
    i.is_credit_note,
    il.quantity,
    il.unit_price,
    il.tax_rate,
    CAST(il.extended_price - il.tax_amount AS DECIMAL(18, 2))              AS total_excluding_tax,
    il.tax_amount,
    il.extended_price                                                      AS total_including_tax,
    il.line_profit                                                         AS profit,
    date_diff('day', o.order_date, i.invoice_date)                         AS days_order_to_invoice,
    date_diff('day', i.invoice_date, CAST(i.confirmed_delivery_time AS DATE)) AS days_invoice_to_delivery
FROM silver.sales_invoicelines il
JOIN silver.sales_invoices i               ON i.invoice_id = il.invoice_id
LEFT JOIN silver.sales_orders o            ON o.order_id = i.order_id
LEFT JOIN silver.warehouse_packagetypes pt ON pt.package_type_id = il.package_type_id;
