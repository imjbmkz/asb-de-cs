-- Q1. Total sales, quantity sold and profit by month and fiscal year.
SELECT
    d.fiscal_year_label                         AS fiscal_year,
    d.fiscal_month_label                        AS fiscal_month,
    d.calendar_month_label                      AS calendar_month,
    count(DISTINCT f.invoice_id)                AS invoices,
    sum(f.quantity)                             AS quantity_sold,
    sum(f.total_excluding_tax)                  AS sales_excl_tax,
    sum(f.total_including_tax)                  AS sales_incl_tax,
    sum(f.profit)                               AS profit,
    round(100.0 * sum(f.profit) / nullif(sum(f.total_excluding_tax), 0), 2) AS margin_pct
FROM gold.fact_sale f
JOIN gold.dim_date d ON d.date_key = f.invoice_date_key
GROUP BY ALL
ORDER BY fiscal_month;
