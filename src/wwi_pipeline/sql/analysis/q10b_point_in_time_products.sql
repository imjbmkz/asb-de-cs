-- Q10b. Same check for products: sales before/after the brand or price change.
SELECT
    s.stock_item_id,
    s.stock_item_name,
    s.stock_item_key,
    s.brand,
    s.unit_price,
    s.valid_from,
    s.valid_to,
    min(d.date)                                 AS first_invoice,
    max(d.date)                                 AS last_invoice,
    sum(f.quantity)                             AS quantity,
    round(avg(f.unit_price), 2)                 AS avg_invoiced_unit_price,
    sum(f.total_excluding_tax)                  AS sales_excl_tax
FROM gold.fact_sale f
JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
JOIN gold.dim_date d       ON d.date_key = f.invoice_date_key
WHERE s.stock_item_id IN (SELECT stock_item_id FROM gold.dim_stock_item GROUP BY 1 HAVING count(*) > 1)
GROUP BY ALL
ORDER BY s.stock_item_id, s.valid_from;
