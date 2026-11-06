-- Q8. Orders containing backordered items and their business impact.
-- An order whose items could not be fully supplied gets a backorder_order_id
-- (a follow-up order holding the outstanding items).
WITH orders AS (
    SELECT order_id, backorder_order_id, any_value(customer_key) AS customer_key,
           sum(quantity) AS qty, sum(total_excluding_tax) AS value
    FROM gold.fact_order GROUP BY order_id, backorder_order_id
),
summary AS (
    SELECT
        count(*)                                             AS total_orders,
        count(*) FILTER (WHERE o.backorder_order_id IS NOT NULL) AS orders_with_backorder,
        sum(o.value)                                         AS total_order_value,
        sum(o.value) FILTER (WHERE o.backorder_order_id IS NOT NULL) AS value_of_orders_with_backorder,
        sum(b.value)                                         AS backordered_value
    FROM orders o
    LEFT JOIN (SELECT order_id, value FROM orders) b ON b.order_id = o.backorder_order_id
)
SELECT
    total_orders,
    orders_with_backorder,
    round(100.0 * orders_with_backorder / total_orders, 2)            AS pct_orders_with_backorder,
    total_order_value,
    value_of_orders_with_backorder,
    backordered_value,
    round(100.0 * backordered_value / total_order_value, 2)          AS backordered_value_pct
FROM summary;
