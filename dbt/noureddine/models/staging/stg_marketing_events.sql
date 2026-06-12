{{ config(materialized='view') }}
SELECT
    event_id::uuid             AS event_id,
    customer_id::uuid          AS customer_id,
    source,
    campaign_name,
    event_type,
    event_timestamp
FROM {{ source('oltp', 'marketing_events') }}
