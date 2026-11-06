-- Q9. How tracked (SCD2) customer and product attributes changed over time.
SELECT 'customer' AS dimension, customer_id AS business_key, customer_key AS surrogate_key,
       customer_name AS name,
       'category=' || customer_category || '; buying_group=' || buying_group ||
       '; credit_limit=' || coalesce(CAST(credit_limit AS VARCHAR), 'none') || '; payment_days=' || payment_days AS tracked_attributes,
       valid_from, valid_to, is_current
FROM gold.dim_customer
WHERE customer_id IN (SELECT customer_id FROM gold.dim_customer GROUP BY 1 HAVING count(*) > 1)
UNION ALL
SELECT 'stock_item', stock_item_id, stock_item_key, stock_item_name,
       'brand=' || brand || '; unit_price=' || unit_price || '; rrp=' || coalesce(CAST(recommended_retail_price AS VARCHAR), ''),
       valid_from, valid_to, is_current
FROM gold.dim_stock_item
WHERE stock_item_id IN (SELECT stock_item_id FROM gold.dim_stock_item GROUP BY 1 HAVING count(*) > 1)
ORDER BY dimension, business_key, valid_from;
