-- Q2a. Products generating the highest sales and profit (top 15).
-- Grouped by business key so that all SCD2 versions of a product are combined.
SELECT
    s.stock_item_id,
    any_value(s.stock_item_name)                AS stock_item,
    any_value(s.primary_stock_group)            AS category,
    sum(f.quantity)                             AS quantity_sold,
    sum(f.total_excluding_tax)                  AS sales_excl_tax,
    sum(f.profit)                               AS profit
FROM gold.fact_sale f
JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
GROUP BY s.stock_item_id
ORDER BY sales_excl_tax DESC
LIMIT 15;
