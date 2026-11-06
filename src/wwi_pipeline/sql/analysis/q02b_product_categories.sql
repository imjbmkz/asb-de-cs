-- Q2b. Product categories (primary stock group) by sales and profit.
SELECT
    s.primary_stock_group                       AS category,
    count(DISTINCT s.stock_item_id)             AS products,
    sum(f.quantity)                             AS quantity_sold,
    sum(f.total_excluding_tax)                  AS sales_excl_tax,
    sum(f.profit)                               AS profit,
    round(100.0 * sum(f.total_excluding_tax) / sum(sum(f.total_excluding_tax)) OVER (), 2) AS share_of_sales_pct
FROM gold.fact_sale f
JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
GROUP BY ALL
ORDER BY sales_excl_tax DESC;
