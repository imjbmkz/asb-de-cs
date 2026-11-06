-- Q10. Historical attributes attached to transactions before and after an SCD change.
-- Facts are joined to the dimension row they were resolved to at load time, so
-- sales made before the change keep the old attributes.
SELECT
    c.customer_id,
    c.customer_name,
    c.customer_key,
    c.customer_category,
    c.buying_group,
    c.credit_limit,
    c.payment_days,
    c.valid_from,
    c.valid_to,
    min(d.date)                                 AS first_invoice,
    max(d.date)                                 AS last_invoice,
    count(DISTINCT f.invoice_id)                AS invoices,
    sum(f.total_excluding_tax)                  AS revenue_excl_tax
FROM gold.fact_sale f
JOIN gold.dim_customer c ON c.customer_key = f.customer_key
JOIN gold.dim_date d     ON d.date_key = f.invoice_date_key
WHERE c.customer_id IN (SELECT customer_id FROM gold.dim_customer GROUP BY 1 HAVING count(*) > 1)
GROUP BY ALL
ORDER BY c.customer_id, c.valid_from;
