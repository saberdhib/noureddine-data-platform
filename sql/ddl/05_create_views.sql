-- =============================================================================
-- 05_create_views.sql
-- Analytical views on the gold schema for dashboarding / quick queries.
-- Idempotent: uses CREATE OR REPLACE.
-- =============================================================================

-- Daily revenue and margin aggregated by date
CREATE OR REPLACE VIEW gold.v_daily_revenue AS
SELECT
    dd.date,
    dd.year,
    dd.month,
    dd.week,
    SUM(fs.revenue)         AS total_revenue,
    SUM(fs.discount)        AS total_discount,
    SUM(fs.shipping_cost)   AS total_shipping,
    SUM(fs.margin)          AS total_margin,
    COUNT(DISTINCT fs.order_id)  AS order_count,
    SUM(fs.quantity)        AS units_sold
FROM gold.fact_sales fs
JOIN gold.dim_date dd ON dd.date_key = fs.date_key
GROUP BY dd.date, dd.year, dd.month, dd.week;

-- Revenue broken down by Islamic cultural calendar event
CREATE OR REPLACE VIEW gold.v_sales_by_calendar_event AS
SELECT
    dce.event_name,
    dce.event_type,
    dd.year,
    SUM(fs.revenue)             AS total_revenue,
    SUM(fs.discount)            AS total_discount,
    SUM(fs.margin)              AS total_margin,
    COUNT(DISTINCT fs.order_id) AS order_count,
    SUM(fs.quantity)            AS units_sold,
    ROUND(AVG(fs.revenue / NULLIF(fs.quantity, 0)), 2) AS avg_unit_revenue
FROM gold.fact_sales fs
JOIN gold.dim_calendar_event dce ON dce.calendar_event_key = fs.calendar_event_key
JOIN gold.dim_date dd ON dd.date_key = fs.date_key
GROUP BY dce.event_name, dce.event_type, dd.year;

-- Top products by revenue
CREATE OR REPLACE VIEW gold.v_top_products AS
SELECT
    dp.sku,
    dp.product_name,
    dp.category,
    dp.seasonality_tag,
    SUM(fs.revenue)             AS total_revenue,
    SUM(fs.quantity)            AS units_sold,
    COUNT(DISTINCT fs.order_id) AS order_count
FROM gold.fact_sales fs
JOIN gold.dim_product dp ON dp.product_key = fs.product_key
GROUP BY dp.sku, dp.product_name, dp.category, dp.seasonality_tag
ORDER BY total_revenue DESC;
