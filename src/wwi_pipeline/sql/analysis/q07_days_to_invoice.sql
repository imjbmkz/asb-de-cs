-- Q7. Average time from order to invoice (and invoice to delivery), by invoice month.
WITH invoices AS (
    SELECT DISTINCT invoice_id, invoice_date_key, days_order_to_invoice, days_invoice_to_delivery
    FROM gold.fact_sale
    WHERE order_id IS NOT NULL
)
SELECT
    coalesce(d.calendar_month_label, 'ALL')     AS invoice_month,
    count(*)                                    AS invoices,
    round(avg(days_order_to_invoice), 2)        AS avg_days_order_to_invoice,
    max(days_order_to_invoice)                  AS max_days_order_to_invoice,
    round(avg(days_invoice_to_delivery), 2)     AS avg_days_invoice_to_delivery
FROM invoices i
JOIN gold.dim_date d ON d.date_key = i.invoice_date_key
GROUP BY ROLLUP (d.calendar_month_label)
ORDER BY d.calendar_month_label NULLS LAST;
