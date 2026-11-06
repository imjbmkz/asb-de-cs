-- Q5. Salespeople by value of orders managed (fact_order) and sales invoiced (fact_sale).
WITH orders AS (
    SELECT salesperson_key, count(DISTINCT order_id) AS orders, sum(total_excluding_tax) AS order_value
    FROM gold.fact_order GROUP BY 1
),
sales AS (
    SELECT salesperson_key, count(DISTINCT invoice_id) AS invoices,
           sum(total_excluding_tax) AS sales_value, sum(profit) AS profit
    FROM gold.fact_sale GROUP BY 1
)
SELECT
    e.full_name                                 AS salesperson,
    o.orders,
    o.order_value,
    round(o.order_value / o.orders, 2)          AS avg_order_value,
    s.invoices,
    s.sales_value,
    s.profit
FROM gold.dim_employee e
JOIN orders o ON o.salesperson_key = e.employee_key
LEFT JOIN sales s ON s.salesperson_key = e.employee_key
ORDER BY o.order_value DESC;
