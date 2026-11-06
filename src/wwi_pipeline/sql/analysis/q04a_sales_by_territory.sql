-- Q4a. Sales and profit by sales territory and state/province.
SELECT
    ci.sales_territory,
    ci.state_province,
    count(DISTINCT ci.city_id)                  AS cities,
    sum(f.total_excluding_tax)                  AS sales_excl_tax,
    sum(f.profit)                               AS profit
FROM gold.fact_sale f
JOIN gold.dim_city ci ON ci.city_key = f.city_key
GROUP BY ALL
ORDER BY ci.sales_territory, sales_excl_tax DESC;
