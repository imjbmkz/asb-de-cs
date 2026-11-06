-- Q6. Proportion of ordered quantity that is later invoiced, by order month.
-- Invoice lines reference the order (order_id) and the product, so ordered and
-- invoiced quantities are matched on (order_id, stock_item_id).
WITH ordered AS (
    SELECT f.order_id, s.stock_item_id, d.calendar_month_label AS order_month, sum(f.quantity) AS ordered_qty
    FROM gold.fact_order f
    JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
    JOIN gold.dim_date d ON d.date_key = f.order_date_key
    GROUP BY ALL
),
invoiced AS (
    SELECT f.order_id, s.stock_item_id, sum(f.quantity) AS invoiced_qty
    FROM gold.fact_sale f
    JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
    WHERE f.order_id IS NOT NULL
    GROUP BY ALL
)
SELECT
    coalesce(o.order_month, 'TOTAL')            AS order_month,
    sum(o.ordered_qty)                          AS ordered_qty,
    sum(coalesce(i.invoiced_qty, 0))            AS invoiced_qty,
    round(100.0 * sum(coalesce(i.invoiced_qty, 0)) / sum(o.ordered_qty), 2) AS invoiced_pct
FROM ordered o
LEFT JOIN invoiced i USING (order_id, stock_item_id)
GROUP BY ROLLUP (o.order_month)
ORDER BY o.order_month NULLS LAST;
