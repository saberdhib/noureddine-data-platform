{{ config(materialized='view') }}
SELECT
    customer_id::uuid          AS customer_id,
    LOWER(email)               AS email,
    first_name,
    last_name,
    country,
    city,
    consent_marketing,
    acquisition_source,
    created_at,
    updated_at
FROM {{ source('oltp', 'customers') }}
