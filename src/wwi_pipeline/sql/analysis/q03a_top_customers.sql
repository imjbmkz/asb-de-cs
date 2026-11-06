-- Q3a. Customers contributing the most revenue (top 15, all versions combined).
SELECT
    c.customer_id,
    any_value(c.customer_name)                  AS customer,
    count(DISTINCT f.invoice_id)                AS invoices,
    sum(f.total_excluding_tax)                  AS revenue_excl_tax,
    sum(f.profit)                               AS profit
FROM gold.fact_sale f
JOIN gold.dim_customer c ON c.customer_key = f.customer_key
GROUP BY c.customer_id
ORDER BY revenue_excl_tax DESC
LIMIT 15;
