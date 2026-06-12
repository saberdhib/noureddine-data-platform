{{ config(materialized='view') }}
SELECT
    order_item_id::uuid        AS order_item_id,
    order_id::uuid             AS order_id,
    product_id::uuid           AS product_id,
    quantity,
    unit_price,
    line_total
FROM {{ source('oltp', 'order_items') }}
