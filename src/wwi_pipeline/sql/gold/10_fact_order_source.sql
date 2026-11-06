-- Resolve surrogate keys for fact_order (grain: one row per order line).
-- SCD2 dimensions are joined on business key AND the transaction date
-- (order_date within [valid_from, valid_to)), so each fact points to the
-- dimension version that was valid when the order was placed.
-- Unmatched lookups resolve to the Unknown member (key 0).
CREATE OR REPLACE TABLE stage.fact_order_source AS
WITH resolved AS (
    SELECT
        s.order_line_id,
        s.order_id,
        s.backorder_order_id,
        coalesce(od.date_key, -1)                       AS order_date_key,
        coalesce(ed.date_key, -1)                       AS expected_delivery_date_key,
        pd.date_key                                     AS picked_date_key,
        coalesce(dc.customer_key, 0)                    AS customer_key,
        coalesce(ci.city_key, 0)                        AS city_key,
        coalesce(sp.employee_key, 0)                    AS salesperson_key,
        coalesce(pk.employee_key, 0)                    AS picker_key,
        coalesce(si.stock_item_key, 0)                  AS stock_item_key,
        s.description,
        s.package,
        s.customer_purchase_order_number,
        s.is_undersupply_backordered,
        s.quantity,
        s.picked_quantity,
        s.unit_price,
        s.tax_rate,
        s.total_excluding_tax,
        s.tax_amount,
        CAST(s.total_excluding_tax + s.tax_amount AS DECIMAL(18, 2)) AS total_including_tax
    FROM stage.order_line s
    LEFT JOIN gold.dim_date od ON od.date = s.order_date
    LEFT JOIN gold.dim_date ed ON ed.date = s.expected_delivery_date
    LEFT JOIN gold.dim_date pd ON pd.date = s.picked_date
    LEFT JOIN gold.dim_customer dc
           ON dc.customer_id = s.customer_id
          AND CAST(s.order_date AS TIMESTAMP) >= dc.valid_from
          AND CAST(s.order_date AS TIMESTAMP) <  dc.valid_to
    LEFT JOIN gold.dim_city ci ON ci.city_id = dc.delivery_city_id AND ci.is_current
    LEFT JOIN gold.dim_employee sp ON sp.employee_id = s.salesperson_person_id AND sp.is_current
    LEFT JOIN gold.dim_employee pk ON pk.employee_id = s.picked_by_person_id AND pk.is_current
    LEFT JOIN gold.dim_stock_item si
           ON si.stock_item_id = s.stock_item_id
          AND CAST(s.order_date AS TIMESTAMP) >= si.valid_from
          AND CAST(s.order_date AS TIMESTAMP) <  si.valid_to
)
SELECT r.*, md5(CAST(to_json(r) AS VARCHAR)) AS _row_hash
FROM resolved r;
