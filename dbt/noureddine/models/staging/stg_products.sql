{{ config(materialized='view') }}
SELECT
    product_id::uuid           AS product_id,
    sku,
    product_name,
    category_id::uuid          AS category_id,
    price_eur,
    cost_eur,
    seasonality_tag,
    created_at,
    updated_at
FROM {{ source('oltp', 'products') }}
