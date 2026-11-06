-- Q3b. Revenue by customer category - using the category valid at invoice time (SCD2).
SELECT
    c.customer_category,
    count(DISTINCT c.customer_id)               AS customers,
    sum(f.total_excluding_tax)                  AS revenue_excl_tax,
    sum(f.profit)                               AS profit,
    round(100.0 * sum(f.total_excluding_tax) / sum(sum(f.total_excluding_tax)) OVER (), 2) AS share_of_revenue_pct
FROM gold.fact_sale f
JOIN gold.dim_customer c ON c.customer_key = f.customer_key
GROUP BY ALL
ORDER BY revenue_excl_tax DESC;
