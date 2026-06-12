{{ config(materialized='view') }}
SELECT
    category_id::uuid          AS category_id,
    category_name,
    created_at
FROM {{ source('oltp', 'categories') }}
