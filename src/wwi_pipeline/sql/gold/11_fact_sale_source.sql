-- Resolve surrogate keys for fact_sale (grain: one row per invoice line).
-- SCD2 dimensions are joined on business key AND invoice_date within
-- [valid_from, valid_to).  Unmatched lookups resolve to the Unknown member (0).
CREATE OR REPLACE TABLE stage.fact_sale_source AS
WITH resolved AS (
    SELECT
        s.invoice_line_id,
        s.invoice_id,
        s.order_id,
        coalesce(idt.date_key, -1)                      AS invoice_date_key,
        odt.date_key                                    AS order_date_key,
        ddt.date_key                                    AS delivery_date_key,
        coalesce(dc.customer_key, 0)                    AS customer_key,
        coalesce(bt.customer_key, 0)                    AS bill_to_customer_key,
        coalesce(ci.city_key, 0)                        AS city_key,
        coalesce(sp.employee_key, 0)                    AS salesperson_key,
        coalesce(si.stock_item_key, 0)                  AS stock_item_key,
        coalesce(dm.delivery_method_key, 0)             AS delivery_method_key,
        s.description,
        s.package,
        s.is_credit_note,
        s.quantity,
        s.unit_price,
        s.tax_rate,
        s.total_excluding_tax,
        s.tax_amount,
        s.total_including_tax,
        s.profit,
        s.days_order_to_invoice,
        s.days_invoice_to_delivery
    FROM stage.sale s
    LEFT JOIN gold.dim_date idt ON idt.date = s.invoice_date
    LEFT JOIN gold.dim_date odt ON odt.date = s.order_date
    LEFT JOIN gold.dim_date ddt ON ddt.date = s.delivery_date
    LEFT JOIN gold.dim_customer dc
           ON dc.customer_id = s.customer_id
          AND CAST(s.invoice_date AS TIMESTAMP) >= dc.valid_from
          AND CAST(s.invoice_date AS TIMESTAMP) <  dc.valid_to
    LEFT JOIN gold.dim_customer bt
           ON bt.customer_id = s.bill_to_customer_id
          AND CAST(s.invoice_date AS TIMESTAMP) >= bt.valid_from
          AND CAST(s.invoice_date AS TIMESTAMP) <  bt.valid_to
    LEFT JOIN gold.dim_city ci ON ci.city_id = dc.delivery_city_id AND ci.is_current
    LEFT JOIN gold.dim_employee sp ON sp.employee_id = s.salesperson_person_id AND sp.is_current
    LEFT JOIN gold.dim_stock_item si
           ON si.stock_item_id = s.stock_item_id
          AND CAST(s.invoice_date AS TIMESTAMP) >= si.valid_from
          AND CAST(s.invoice_date AS TIMESTAMP) <  si.valid_to
    LEFT JOIN gold.dim_delivery_method dm ON dm.delivery_method_id = s.delivery_method_id AND dm.is_current
)
SELECT r.*, md5(CAST(to_json(r) AS VARCHAR)) AS _row_hash
FROM resolved r;
