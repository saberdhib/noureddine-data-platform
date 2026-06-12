{{ config(materialized='table', schema='gold') }}
SELECT
    MD5(customer_id::text)                       AS customer_key,
    customer_id,
    country,
    city,
    CASE
        WHEN consent_marketing THEN 'engaged'
        ELSE 'standard'
    END                                          AS segment,
    acquisition_source
FROM {{ ref('stg_customers') }}
