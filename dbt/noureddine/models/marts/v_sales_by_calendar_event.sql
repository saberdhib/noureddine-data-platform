{{ config(materialized='view', schema='gold') }}
-- Revenue broken down by Islamic + retail calendar event (gold).
SELECT
    dce.event_name,
    dce.event_type,
    dd.year,
    SUM(fs.revenue)              AS total_revenue,
    SUM(fs.discount)             AS total_discount,
    SUM(fs.margin)               AS total_margin,
    COUNT(DISTINCT fs.order_id)  AS order_count,
    SUM(fs.quantity)             AS units_sold,
    ROUND(AVG(fs.revenue / NULLIF(fs.quantity, 0)), 2) AS avg_unit_revenue
FROM {{ ref('fact_sales') }} fs
JOIN {{ ref('dim_calendar_event') }} dce ON dce.calendar_event_key = fs.calendar_event_key
JOIN {{ ref('dim_date') }} dd ON dd.date_key = fs.date_key
GROUP BY dce.event_name, dce.event_type, dd.year
