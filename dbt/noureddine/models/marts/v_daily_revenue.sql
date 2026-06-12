{{ config(materialized='view', schema='gold') }}
-- Daily revenue / margin (gold). dbt-owned so it survives fact_sales rebuilds.
SELECT
    dd.date,
    dd.year,
    dd.month,
    dd.week,
    SUM(fs.revenue)              AS total_revenue,
    SUM(fs.discount)             AS total_discount,
    SUM(fs.shipping_cost)        AS total_shipping,
    SUM(fs.margin)               AS total_margin,
    COUNT(DISTINCT fs.order_id)  AS order_count,
    SUM(fs.quantity)             AS units_sold
FROM {{ ref('fact_sales') }} fs
JOIN {{ ref('dim_date') }} dd ON dd.date_key = fs.date_key
GROUP BY dd.date, dd.year, dd.month, dd.week
