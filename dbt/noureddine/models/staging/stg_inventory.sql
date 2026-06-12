{{ config(materialized='view') }}
SELECT
    inventory_id::uuid  AS inventory_id,
    product_id::uuid    AS product_id,
    stock_quantity,
    reorder_threshold,
    last_updated
FROM {{ source('oltp', 'inventory') }}
