-- Q8b. Backordered value by customer category (top impact).
WITH orders AS (
    SELECT order_id, backorder_order_id, any_value(customer_key) AS customer_key,
           sum(total_excluding_tax) AS value
    FROM gold.fact_order GROUP BY order_id, backorder_order_id
)
SELECT
    c.customer_category,
    count(*)                                    AS orders_with_backorder,
    sum(b.value)                                AS backordered_value,
    round(avg(b.value), 2)                      AS avg_backordered_value
FROM orders o
JOIN orders b ON b.order_id = o.backorder_order_id
JOIN gold.dim_customer c ON c.customer_key = o.customer_key
GROUP BY ALL
ORDER BY backordered_value DESC;
