# Business query results

_Generated 2026-11-06 11:46 from the gold star schema. SQL files: `src/wwi_pipeline/sql/analysis/`._

## Q1. Total sales, quantity sold and profit by month and fiscal year.

<details><summary>SQL</summary>

```sql
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
```
</details>

| fiscal_year | fiscal_month | calendar_month | invoices | quantity_sold | sales_excl_tax | sales_incl_tax | profit | margin_pct |
|---|---|---|---|---|---|---|---|---|
| FY2016 | FY2016-M08 | 2016-06 | 296862 | 22363038 | 477,387,247.30 | 548,486,278.22 | 228,855,227.20 | 47.94 |
| FY2016 | FY2016-M09 | 2016-07 | 286599 | 6027378 | 181,396,129.50 | 208,428,478.18 | 91,157,453.80 | 50.25 |

## Q2a. Products generating the highest sales and profit (top 15).

<details><summary>SQL</summary>

```sql
-- Q2a. Products generating the highest sales and profit (top 15).
-- Grouped by business key so that all SCD2 versions of a product are combined.
SELECT
    s.stock_item_id,
    any_value(s.stock_item_name)                AS stock_item,
    any_value(s.primary_stock_group)            AS category,
    sum(f.quantity)                             AS quantity_sold,
    sum(f.total_excluding_tax)                  AS sales_excl_tax,
    sum(f.profit)                               AS profit
FROM gold.fact_sale f
JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
GROUP BY s.stock_item_id
ORDER BY sales_excl_tax DESC
LIMIT 15;
```
</details>

| stock_item_id | stock_item | category | quantity_sold | sales_excl_tax | profit |
|---|---|---|---|---|---|
| 167 | 10 mm Anti static bubble wrap (Blue) 50m | Packaging Materials | 334790 | 33,144,210.00 | 18,078,660.00 |
| 170 | 20 mm Anti static bubble wrap (Blue) 50m | Packaging Materials | 296980 | 30,291,960.00 | 13,958,060.00 |
| 215 | Air cushion machine (Blue) | Packaging Materials | 13376 | 25,401,024.00 | 10,152,384.00 |
| 161 | 20 mm Double sided bubble wrap 50m | Packaging Materials | 202400 | 21,859,200.00 | 18,620,800.00 |
| 75 | Ride on big wheel monster truck (Black) 1/12 scale | Toys | 54385 | 18,762,825.00 | 7,613,900.00 |
| 74 | Ride on vintage American toy coupe (Black) 1/12 scale | Toys | 53643 | 15,288,255.00 | 6,973,590.00 |
| 172 | 32 mm Anti static bubble wrap (Blue) 20m | Packaging Materials | 315480 | 15,143,040.00 | 7,887,000.00 |
| 73 | Ride on vintage American toy coupe (Red) 1/12 scale | Toys | 52667 | 15,010,095.00 | 6,846,710.00 |
| 69 | Ride on toy sedan car (Blue) 1/12 scale | Toys | 54454 | 12,524,420.00 | 4,628,590.00 |
| 67 | Ride on toy sedan car (Black) 1/12 scale | Toys | 54413 | 12,514,990.00 | 4,625,105.00 |
| 68 | Ride on toy sedan car (Red) 1/12 scale | Toys | 54092 | 12,441,160.00 | 4,597,820.00 |
| 72 | Ride on toy sedan car (Pink) 1/12 scale | Toys | 52904 | 12,167,920.00 | 4,496,840.00 |
| 70 | Ride on toy sedan car (Green) 1/12 scale | Toys | 52694 | 12,119,620.00 | 4,478,990.00 |
| 71 | Ride on toy sedan car (Yellow) 1/12 scale | Toys | 52506 | 12,076,380.00 | 4,463,010.00 |
| 155 | Large sized bubblewrap roll 50m | Packaging Materials | 490570 | 11,773,680.00 | 5,396,270.00 |

## Q2b. Product categories (primary stock group) by sales and profit.

<details><summary>SQL</summary>

```sql
-- Q2b. Product categories (primary stock group) by sales and profit.
SELECT
    s.primary_stock_group                       AS category,
    count(DISTINCT s.stock_item_id)             AS products,
    sum(f.quantity)                             AS quantity_sold,
    sum(f.total_excluding_tax)                  AS sales_excl_tax,
    sum(f.profit)                               AS profit,
    round(100.0 * sum(f.total_excluding_tax) / sum(sum(f.total_excluding_tax)) OVER (), 2) AS share_of_sales_pct
FROM gold.fact_sale f
JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
GROUP BY ALL
ORDER BY sales_excl_tax DESC;
```
</details>

| category | products | quantity_sold | sales_excl_tax | profit | share_of_sales_pct |
|---|---|---|---|---|---|
| Packaging Materials | 67 | 13514318 | 276,291,765.20 | 143,930,688.40 | 41.94 |
| Toys | 21 | 1074302 | 138,321,225.00 | 57,084,687.00 | 21.00 |
| T-Shirts | 26 | 3362832 | 60,530,976.00 | 34,982,166.00 | 9.19 |
| Clothing | 24 | 2970448 | 56,405,803.00 | 4,943,638.00 | 8.56 |
| USB Novelties | 14 | 747070 | 39,872,351.20 | 22,940,671.70 | 6.05 |
| Furry Footwear | 24 | 2660737 | 39,456,344.00 | 29,047,216.50 | 5.99 |
| Mugs | 42 | 2245983 | 29,197,779.00 | 19,090,855.50 | 4.43 |
| Novelty Items | 8 | 1545336 | 13,723,418.40 | 6,039,680.40 | 2.08 |
| Computing Novelties | 1 | 269390 | 4,983,715.00 | 1,953,077.50 | 0.76 |

## Q3a. Customers contributing the most revenue (top 15, all versions combined).

<details><summary>SQL</summary>

```sql
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
```
</details>

| customer_id | customer | invoices | revenue_excl_tax | profit |
|---|---|---|---|---|
| 999 | Kristi Part | 874 | 1,217,862.00 | 619,286.30 |
| 822 | Suparna Bhattacharya | 906 | 1,187,355.25 | 580,468.35 |
| 980 | Om Yadav | 976 | 1,180,944.75 | 570,905.20 |
| 159 | Tailspin Toys (Saint Louis Park, MN) | 945 | 1,175,031.65 | 569,609.05 |
| 500 | Wingtip Toys (Obion, TN) | 917 | 1,166,910.40 | 578,577.30 |
| 548 | Wingtip Toys (Indian Creek, IL) | 901 | 1,151,896.55 | 568,390.80 |
| 802 | Cosmina Vlad | 954 | 1,149,559.45 | 552,477.45 |
| 830 | Jana Fialova | 925 | 1,133,826.70 | 562,319.80 |
| 448 | Wingtip Toys (Salt Wells, NV) | 930 | 1,133,348.50 | 558,856.25 |
| 524 | Wingtip Toys (Cloquet, MN) | 906 | 1,131,559.60 | 563,344.75 |
| 523 | Wingtip Toys (Bruceton Mills, WV) | 928 | 1,129,235.35 | 553,974.50 |
| 515 | Wingtip Toys (Del Valle, TX) | 911 | 1,120,466.30 | 538,716.05 |
| 819 | Santiago Vera | 919 | 1,120,137.50 | 535,364.75 |
| 458 | Wingtip Toys (Coker, AL) | 860 | 1,119,473.00 | 564,249.10 |
| 1045 | Matteo Cattaneo | 921 | 1,119,161.45 | 559,818.80 |

## Q3b. Revenue by customer category - using the category valid at invoice time (SCD2).

<details><summary>SQL</summary>

```sql
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
```
</details>

| customer_category | customers | revenue_excl_tax | profit | share_of_revenue_pct |
|---|---|---|---|---|
| Novelty Shop | 460 | 454,243,399.70 | 219,733,439.10 | 68.95 |
| Supermarket | 60 | 58,154,781.80 | 28,517,213.35 | 8.83 |
| Computer Store | 51 | 50,768,680.60 | 24,953,712.05 | 7.71 |
| Gift Store | 49 | 48,698,076.35 | 23,822,712.95 | 7.39 |
| Corporate | 47 | 46,918,438.35 | 22,985,603.55 | 7.12 |

## Q4a. Sales and profit by sales territory and state/province.

<details><summary>SQL</summary>

```sql
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
```
</details>

| sales_territory | state_province | cities | sales_excl_tax | profit |
|---|---|---|---|---|
| External | Puerto Rico (US Territory) | 8 | 9,876,126.10 | 4,789,047.15 |
| Far West | California | 34 | 32,267,823.25 | 15,704,747.10 |
| Far West | Washington | 17 | 16,758,737.00 | 8,063,385.70 |
| Far West | Alaska | 11 | 12,041,823.05 | 5,792,620.35 |
| Far West | Oregon | 8 | 7,547,379.20 | 3,726,230.20 |
| Far West | Nevada | 5 | 5,294,337.15 | 2,568,723.95 |
| Far West | Hawaii | 1 | 876,826.10 | 436,312.40 |
| Great Lakes | Ohio | 21 | 21,123,845.65 | 10,227,481.85 |
| Great Lakes | Illinois | 18 | 18,567,001.95 | 9,050,178.60 |
| Great Lakes | Michigan | 13 | 12,833,086.10 | 6,202,325.00 |
| Great Lakes | Indiana | 12 | 12,018,241.70 | 5,911,448.40 |
| Great Lakes | Wisconsin | 12 | 11,907,412.10 | 5,793,881.55 |
| Mideast | Pennsylvania | 37 | 36,883,256.15 | 17,968,834.50 |
| Mideast | New York | 35 | 35,252,273.45 | 17,080,801.60 |
| Mideast | New Jersey | 18 | 17,690,185.10 | 8,598,098.00 |
| Mideast | Maryland | 8 | 8,004,148.75 | 3,858,793.00 |
| New England | Massachusetts[E] | 11 | 10,883,087.85 | 5,240,367.55 |
| New England | Maine | 8 | 7,806,996.00 | 3,796,270.60 |
| New England | New Hampshire | 5 | 4,956,057.05 | 2,465,241.35 |
| New England | Vermont | 5 | 4,853,294.25 | 2,346,776.90 |
| New England | Connecticut | 4 | 3,946,101.90 | 1,925,721.15 |
| Plains | Minnesota | 19 | 19,044,336.85 | 9,264,219.90 |
| Plains | Missouri | 18 | 17,941,384.95 | 8,683,109.80 |
| Plains | Kansas | 13 | 13,359,854.85 | 6,492,505.40 |
| Plains | Iowa | 12 | 12,138,755.05 | 5,938,890.50 |
| Plains | North Dakota | 10 | 9,794,029.00 | 4,728,524.30 |
| Plains | South Dakota | 8 | 7,753,878.00 | 3,775,292.60 |
| Plains | Nebraska | 7 | 6,797,129.65 | 3,277,286.35 |
| Rocky Mountain | Colorado | 18 | 17,748,770.55 | 8,541,907.10 |
| Rocky Mountain | Montana | 8 | 7,856,654.20 | 3,826,118.30 |
| Rocky Mountain | Idaho | 6 | 6,022,996.75 | 2,919,840.00 |
| Rocky Mountain | Wyoming | 5 | 6,013,837.35 | 2,974,655.70 |
| Rocky Mountain | Utah | 5 | 5,001,757.70 | 2,398,396.60 |
| Southeast | Florida | 21 | 20,844,365.70 | 10,177,362.15 |
| Southeast | North Carolina | 19 | 18,029,278.80 | 8,749,981.10 |
| Southeast | Alabama | 16 | 16,125,979.20 | 7,812,554.45 |
| Southeast | South Carolina | 14 | 14,919,901.80 | 7,181,523.30 |
| Southeast | West Virginia | 14 | 14,390,559.10 | 6,982,808.90 |
| Southeast | Louisiana | 13 | 12,688,348.95 | 6,209,924.05 |
| Southeast | Georgia | 12 | 11,706,565.95 | 5,747,905.80 |
| Southeast | Kentucky | 10 | 9,981,447.15 | 4,807,021.50 |
| Southeast | Virginia | 9 | 9,011,787.95 | 4,350,856.45 |
| Southeast | Arkansas | 8 | 7,773,265.80 | 3,793,682.65 |
| Southeast | Mississippi | 5 | 5,135,288.15 | 2,474,662.15 |
| Southeast | Tennessee | 5 | 4,959,593.45 | 2,413,204.95 |
| Southwest | Texas | 45 | 45,640,517.75 | 22,220,188.50 |
| Southwest | Oklahoma | 19 | 19,112,645.40 | 9,389,182.40 |
| Southwest | New Mexico | 18 | 17,696,873.90 | 8,545,867.35 |
| Southwest | Arizona | 10 | 9,905,533.00 | 4,787,921.85 |

## Q4b. Top 15 cities by sales.

<details><summary>SQL</summary>

```sql
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
```
</details>

| city | state_province | sales_territory | sales_excl_tax | profit |
|---|---|---|---|---|
| Akhiok | Alaska | Far West | 2,122,052.15 | 1,043,879.90 |
| Teutopolis | Illinois | Great Lakes | 2,052,947.15 | 970,837.50 |
| Cherry Grove Beach | South Carolina | Southeast | 2,022,105.50 | 960,294.10 |
| Sinclair | Wyoming | Rocky Mountain | 2,021,684.45 | 961,230.20 |
| Isabela | Puerto Rico (US Territory) | External | 2,008,445.75 | 974,232.65 |
| East Fultonham | Ohio | Great Lakes | 1,987,104.15 | 928,440.75 |
| Rockwall | Texas | Southwest | 1,957,321.90 | 954,142.15 |
| Palmas del Mar | Puerto Rico (US Territory) | External | 1,931,206.70 | 942,187.35 |
| Yerington | Nevada | Far West | 1,217,862.00 | 619,286.30 |
| Tiff City | Missouri | Plains | 1,187,355.25 | 580,468.35 |
| Lunds | Wisconsin | Great Lakes | 1,180,944.75 | 570,905.20 |
| Saint Louis Park | Minnesota | Plains | 1,175,031.65 | 569,609.05 |
| Obion | Tennessee | Southeast | 1,166,910.40 | 578,577.30 |
| Indian Creek | Illinois | Great Lakes | 1,151,896.55 | 568,390.80 |
| Cañon | New Mexico | Southwest | 1,149,559.45 | 552,477.45 |

## Q5. Salespeople by value of orders managed (fact_order) and sales invoiced (fact_sale).

<details><summary>SQL</summary>

```sql
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
```
</details>

| salesperson | orders | order_value | avg_order_value | invoices | sales_value | profit |
|---|---|---|---|---|---|---|
| Archer Lamble | 107548 | 173,982,453.90 | 1,617.72 | 58645 | 66,185,803.65 | 32,049,301.85 |
| Kayla Woodcock | 107156 | 173,128,636.05 | 1,615.67 | 58464 | 66,613,909.20 | 32,419,584.50 |
| Hudson Onslow | 106836 | 172,763,338.80 | 1,617.09 | 58224 | 65,464,930.95 | 31,857,339.40 |
| Taj Shand | 107077 | 172,543,683.35 | 1,611.40 | 58602 | 66,200,729.00 | 32,181,859.35 |
| Sophia Hinton | 106452 | 172,381,347.55 | 1,619.33 | 58005 | 65,923,066.60 | 32,102,183.95 |
| Jack Potter | 107026 | 172,091,205.80 | 1,607.94 | 58398 | 65,669,978.75 | 31,730,639.30 |
| Hudson Hollinworth | 106882 | 171,929,564.65 | 1,608.59 | 58431 | 65,698,548.30 | 31,931,748.65 |
| Anthony Grosse | 106793 | 171,726,023.10 | 1,608.03 | 58349 | 66,052,838.25 | 32,125,022.35 |
| Lily Code | 106757 | 171,339,099.20 | 1,604.94 | 58182 | 65,622,596.50 | 31,841,512.60 |
| Amy Trefl | 106320 | 170,529,003.35 | 1,603.92 | 58161 | 65,350,975.60 | 31,773,489.05 |

## Q6. Proportion of ordered quantity that is later invoiced, by order month.

<details><summary>SQL</summary>

```sql
-- Q6. Proportion of ordered quantity that is later invoiced, by order month.
-- Invoice lines reference the order (order_id) and the product, so ordered and
-- invoiced quantities are matched on (order_id, stock_item_id).
WITH ordered AS (
    SELECT f.order_id, s.stock_item_id, d.calendar_month_label AS order_month, sum(f.quantity) AS ordered_qty
    FROM gold.fact_order f
    JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
    JOIN gold.dim_date d ON d.date_key = f.order_date_key
    GROUP BY ALL
),
invoiced AS (
    SELECT f.order_id, s.stock_item_id, sum(f.quantity) AS invoiced_qty
    FROM gold.fact_sale f
    JOIN gold.dim_stock_item s ON s.stock_item_key = f.stock_item_key
    WHERE f.order_id IS NOT NULL
    GROUP BY ALL
)
SELECT
    coalesce(o.order_month, 'TOTAL')            AS order_month,
    sum(o.ordered_qty)                          AS ordered_qty,
    sum(coalesce(i.invoiced_qty, 0))            AS invoiced_qty,
    round(100.0 * sum(coalesce(i.invoiced_qty, 0)) / sum(o.ordered_qty), 2) AS invoiced_pct
FROM ordered o
LEFT JOIN invoiced i USING (order_id, stock_item_id)
GROUP BY ROLLUP (o.order_month)
ORDER BY o.order_month NULLS LAST;
```
</details>

| order_month | ordered_qty | invoiced_qty | invoiced_pct |
|---|---|---|---|
| 2016-06 | 45625805 | 23145615 | 50.73 |
| 2016-07 | 49126628 | 5244801 | 10.68 |
| 2016-08 | 465933 | 0 | 0.00 |
| TOTAL | 95218366 | 28390416 | 29.82 |

## Q7. Average time from order to invoice (and invoice to delivery), by invoice month.

<details><summary>SQL</summary>

```sql
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
```
</details>

| invoice_month | invoices | avg_days_order_to_invoice | max_days_order_to_invoice | avg_days_invoice_to_delivery |
|---|---|---|---|---|
| 2016-06 | 296862 | 0.14 | 29 | 20.11 |
| 2016-07 | 286599 | 1.21 | 58 | 19.46 |
| ALL | 583461 | 0.67 | 58 | 19.79 |

## Q8. Orders containing backordered items and their business impact.

<details><summary>SQL</summary>

```sql
-- Q8. Orders containing backordered items and their business impact.
-- An order whose items could not be fully supplied gets a backorder_order_id
-- (a follow-up order holding the outstanding items).
WITH orders AS (
    SELECT order_id, backorder_order_id, any_value(customer_key) AS customer_key,
           sum(quantity) AS qty, sum(total_excluding_tax) AS value
    FROM gold.fact_order GROUP BY order_id, backorder_order_id
),
summary AS (
    SELECT
        count(*)                                             AS total_orders,
        count(*) FILTER (WHERE o.backorder_order_id IS NOT NULL) AS orders_with_backorder,
        sum(o.value)                                         AS total_order_value,
        sum(o.value) FILTER (WHERE o.backorder_order_id IS NOT NULL) AS value_of_orders_with_backorder,
        sum(b.value)                                         AS backordered_value
    FROM orders o
    LEFT JOIN (SELECT order_id, value FROM orders) b ON b.order_id = o.backorder_order_id
)
SELECT
    total_orders,
    orders_with_backorder,
    round(100.0 * orders_with_backorder / total_orders, 2)            AS pct_orders_with_backorder,
    total_order_value,
    value_of_orders_with_backorder,
    backordered_value,
    round(100.0 * backordered_value / total_order_value, 2)          AS backordered_value_pct
FROM summary;
```
</details>

| total_orders | orders_with_backorder | pct_orders_with_backorder | total_order_value | value_of_orders_with_backorder | backordered_value | backordered_value_pct |
|---|---|---|---|---|---|---|
| 1068847 | 434680 | 40.67 | 1,722,414,355.75 | 383,545,898.05 | 873,899,608.90 | 50.74 |

## Q8b. Backordered value by customer category (top impact).

<details><summary>SQL</summary>

```sql
-- Q8b. Backordered value by customer category (top impact).
WITH orders AS (
    SELECT order_id, backorder_order_id, any_value(customer_key) AS customer_key,
           sum(total_excluding_tax) AS value
    FROM gold.fact_order GROUP BY order_id, backorder_order_id
)
SELECT
    c.customer_category,
    count(*)                                    AS orders_with_backorder,
    sum(b.value)                                AS backordered_value,
    round(avg(b.value), 2)                      AS avg_backordered_value
FROM orders o
JOIN orders b ON b.order_id = o.backorder_order_id
JOIN gold.dim_customer c ON c.customer_key = o.customer_key
GROUP BY ALL
ORDER BY backordered_value DESC;
```
</details>

| customer_category | orders_with_backorder | backordered_value | avg_backordered_value |
|---|---|---|---|
| Novelty Shop | 300083 | 604,786,545.10 | 2,015.40 |
| Supermarket | 38283 | 77,152,089.00 | 2,015.31 |
| Computer Store | 33478 | 66,741,384.50 | 1,993.59 |
| Gift Store | 31823 | 63,198,987.25 | 1,985.95 |
| Corporate | 31013 | 62,020,603.05 | 1,999.83 |

## Q9. How tracked (SCD2) customer and product attributes changed over time.

<details><summary>SQL</summary>

```sql
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
```
</details>

| dimension | business_key | surrogate_key | name | tracked_attributes | valid_from | valid_to | is_current |
|---|---|---|---|---|---|---|---|
| customer | 14 | 14 | Tailspin Toys (Long Meadow, MD) | category=Novelty Shop; buying_group=Tailspin Toys; credit_limit=none; payment_days=7 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | False |
| customer | 14 | 1485 | Tailspin Toys (Long Meadow, MD) | category=Novelty Shop; buying_group=Tailspin Toys; credit_limit=5000.00; payment_days=30 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | True |
| customer | 62 | 62 | Tailspin Toys (Great Neck Estates, NY) | category=Novelty Shop; buying_group=Tailspin Toys; credit_limit=none; payment_days=7 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | False |
| customer | 62 | 1486 | Tailspin Toys (Great Neck Estates, NY) | category=Novelty Shop; buying_group=Wingtip Toys; credit_limit=none; payment_days=7 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | True |
| customer | 74 | 74 | Tailspin Toys (Indios, PR) | category=Novelty Shop; buying_group=Tailspin Toys; credit_limit=none; payment_days=7 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | False |
| customer | 74 | 1487 | Tailspin Toys (Indios, PR) | category=Supermarket; buying_group=Tailspin Toys; credit_limit=none; payment_days=7 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | True |
| stock_item | 4 | 4 | USB food flash drive - sushi roll | brand=N/A; unit_price=32.00; rrp=47.84 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | False |
| stock_item | 4 | 228 | USB food flash drive - sushi roll | brand=Northwind; unit_price=32.00; rrp=47.84 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | True |
| stock_item | 10 | 10 | USB food flash drive - chocolate bar | brand=N/A; unit_price=32.00; rrp=47.84 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | False |
| stock_item | 10 | 229 | USB food flash drive - chocolate bar | brand=N/A; unit_price=35.00; rrp=47.84 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | True |

## Q10. Historical attributes attached to transactions before and after an SCD change.

<details><summary>SQL</summary>

```sql
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
```
</details>

| customer_id | customer_name | customer_key | customer_category | buying_group | credit_limit | payment_days | valid_from | valid_to | first_invoice | last_invoice | invoices | revenue_excl_tax |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 14 | Tailspin Toys (Long Meadow, MD) | 14 | Novelty Shop | Tailspin Toys |  | 7 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | 2016-06-01 | 2016-07-14 | 705 | 898,992.45 |
| 14 | Tailspin Toys (Long Meadow, MD) | 1485 | Novelty Shop | Tailspin Toys | 5,000.00 | 30 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | 2016-07-15 | 2016-07-31 | 230 | 126,391.40 |
| 62 | Tailspin Toys (Great Neck Estates, NY) | 62 | Novelty Shop | Tailspin Toys |  | 7 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | 2016-06-01 | 2016-07-14 | 715 | 953,463.15 |
| 62 | Tailspin Toys (Great Neck Estates, NY) | 1486 | Novelty Shop | Wingtip Toys |  | 7 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | 2016-07-15 | 2016-07-31 | 244 | 117,358.75 |
| 74 | Tailspin Toys (Indios, PR) | 74 | Novelty Shop | Tailspin Toys |  | 7 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | 2016-06-01 | 2016-07-14 | 723 | 960,158.80 |
| 74 | Tailspin Toys (Indios, PR) | 1487 | Supermarket | Tailspin Toys |  | 7 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | 2016-07-15 | 2016-07-31 | 224 | 106,977.30 |

## Q10b. Same check for products: sales before/after the brand or price change.

<details><summary>SQL</summary>

```sql
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
```
</details>

| stock_item_id | stock_item_name | stock_item_key | brand | unit_price | valid_from | valid_to | first_invoice | last_invoice | quantity | avg_invoiced_unit_price | sales_excl_tax |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 4 | USB food flash drive - sushi roll | 4 | N/A | 32.00 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | 2016-06-01 | 2016-07-14 | 39300 | 26.48 | 1,042,502.40 |
| 4 | USB food flash drive - sushi roll | 228 | Northwind | 32.00 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | 2016-07-15 | 2016-07-31 | 14963 | 32.00 | 478,816.00 |
| 10 | USB food flash drive - chocolate bar | 10 | N/A | 32.00 | 1900-01-01 00:00:00 | 2016-07-15 00:00:00 | 2016-06-01 | 2016-07-14 | 38917 | 26.77 | 1,040,011.20 |
| 10 | USB food flash drive - chocolate bar | 229 | N/A | 35.00 | 2016-07-15 00:00:00 | 9999-12-31 00:00:00 | 2016-07-15 | 2016-07-31 | 15272 | 32.00 | 488,704.00 |
