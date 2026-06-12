{{ config(materialized='view', schema='gold') }}
-- Top products by revenue (gold).
SELECT
    dp.sku,
    dp.product_name,
    dp.category,
    dp.seasonality_tag,
    SUM(fs.revenue)             AS total_revenue,
    SUM(fs.quantity)            AS units_sold,
    COUNT(DISTINCT fs.order_id) AS order_count
FROM {{ ref('fact_sales') }} fs
JOIN {{ ref('dim_product') }} dp ON dp.product_key = fs.product_key
GROUP BY dp.sku, dp.product_name, dp.category, dp.seasonality_tag
ORDER BY total_revenue DESC
