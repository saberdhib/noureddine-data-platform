{{ config(materialized='view') }}
SELECT
    order_id::uuid             AS order_id,
    customer_id::uuid          AS customer_id,
    order_date,
    order_date::date           AS order_day,
    total_amount,
    discount_amount,
    shipping_cost,
    payment_status,
    order_status,
    COALESCE(acquisition_channel, 'direct') AS acquisition_channel,
    created_at
FROM {{ source('oltp', 'orders') }}
