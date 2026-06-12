{{ config(materialized='table', schema='gold') }}
SELECT
    MD5(p.product_id::text)                       AS product_key,
    p.product_id,
    p.sku,
    p.product_name,
    c.category_name                               AS category,
    p.seasonality_tag
FROM {{ ref('stg_products') }} p
LEFT JOIN {{ ref('stg_categories') }} c ON p.category_id = c.category_id
