-- Q4b. Top 15 cities by sales.
SELECT
    ci.city,
    ci.state_province,
    ci.sales_territory,
    sum(f.total_excluding_tax)                  AS sales_excl_tax,
    sum(f.profit)                               AS profit
FROM gold.fact_sale f
JOIN gold.dim_city ci ON ci.city_key = f.city_key
GROUP BY ALL
ORDER BY sales_excl_tax DESC
LIMIT 15;
