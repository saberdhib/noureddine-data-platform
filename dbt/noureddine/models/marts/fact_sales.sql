{{ config(materialized='table', schema='gold') }}
WITH lines_per_order AS (
    SELECT order_id, COUNT(*) AS n_lines
    FROM {{ ref('stg_order_items') }}
    GROUP BY order_id
),
-- one calendar event per order day (smallest window wins) to preserve fact grain
event_per_order AS (
    SELECT
        o.order_id,
        dce.calendar_event_key
    FROM {{ ref('stg_orders') }} o
    LEFT JOIN LATERAL (
        SELECT calendar_event_key
        FROM {{ ref('dim_calendar_event') }} d
        WHERE o.order_day BETWEEN d.start_date AND d.end_date
        ORDER BY (d.end_date - d.start_date) ASC, d.start_date DESC
        LIMIT 1
    ) dce ON TRUE
)
SELECT
    MD5(oi.order_item_id::text)                   AS sale_key,
    o.order_id,
    dc.customer_key,
    dp.product_key,
    dd.date_key,
    dch.channel_key,
    epo.calendar_event_key,
    oi.quantity,
    oi.line_total                                 AS revenue,
    COALESCE(o.discount_amount / NULLIF(o.total_amount, 0) * oi.line_total, 0) AS discount,
    COALESCE(o.shipping_cost / NULLIF(lpo.n_lines, 0), 0)                       AS shipping_cost,
    oi.line_total - (oi.unit_price * oi.quantity * 0.6)                         AS margin
FROM {{ ref('stg_order_items') }} oi
JOIN {{ ref('stg_orders') }}      o   ON oi.order_id = o.order_id
JOIN lines_per_order              lpo ON o.order_id = lpo.order_id
JOIN event_per_order              epo ON o.order_id = epo.order_id
JOIN {{ ref('dim_customer') }}    dc  ON o.customer_id = dc.customer_id
JOIN {{ ref('dim_product') }}     dp  ON oi.product_id = dp.product_id
JOIN {{ ref('dim_date') }}        dd  ON o.order_day = dd.date
LEFT JOIN {{ ref('dim_channel') }} dch ON o.acquisition_channel = dch.channel_name
