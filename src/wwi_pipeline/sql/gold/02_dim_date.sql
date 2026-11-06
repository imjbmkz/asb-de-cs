-- dim_date: generated calendar.  Covers 2013-01-01 .. 2017-12-31 (the WWI
-- sample period) and is extended automatically to any transaction date found in
-- staging.  WWI's financial year starts on 1 November and is named after the
-- calendar year in which it ends (FY2016 = 2015-11-01 .. 2016-10-31).
-- Insert-only (anti join) => idempotent.
INSERT INTO gold.dim_date
WITH bounds AS (
    SELECT
        least(DATE '2013-01-01', min(d)) AS start_date,
        greatest(DATE '2017-12-31', max(d)) AS end_date
    FROM (
        SELECT order_date AS d FROM stage.order_line
        UNION ALL SELECT expected_delivery_date FROM stage.order_line
        UNION ALL SELECT picked_date FROM stage.order_line
        UNION ALL SELECT invoice_date FROM stage.sale
        UNION ALL SELECT delivery_date FROM stage.sale
    )
),
days AS (
    SELECT CAST(gs AS DATE) AS d
    FROM bounds, generate_series(bounds.start_date::TIMESTAMP, bounds.end_date::TIMESTAMP, INTERVAL 1 DAY) AS t(gs)
)
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER)                    AS date_key,
    d                                                          AS date,
    day(d)                                                     AS day_of_month,
    dayname(d)                                                 AS day_name,
    isodow(d)                                                  AS day_of_week,
    isodow(d) IN (6, 7)                                        AS is_weekend,
    weekofyear(d)                                              AS week_of_year,
    month(d)                                                   AS calendar_month,
    monthname(d)                                               AS calendar_month_name,
    strftime(d, '%Y-%m')                                       AS calendar_month_label,
    quarter(d)                                                 AS calendar_quarter,
    year(d)                                                    AS calendar_year,
    ((month(d) + 1) % 12) + 1                                  AS fiscal_month,
    ((((month(d) + 1) % 12) + 1) - 1) // 3 + 1                 AS fiscal_quarter,
    year(d) + CASE WHEN month(d) >= 11 THEN 1 ELSE 0 END       AS fiscal_year,
    'FY' || (year(d) + CASE WHEN month(d) >= 11 THEN 1 ELSE 0 END)
         || '-M' || lpad(CAST(((month(d) + 1) % 12) + 1 AS VARCHAR), 2, '0') AS fiscal_month_label,
    'FY' || (year(d) + CASE WHEN month(d) >= 11 THEN 1 ELSE 0 END) AS fiscal_year_label
FROM days
WHERE NOT EXISTS (SELECT 1 FROM gold.dim_date dd WHERE dd.date = days.d);
