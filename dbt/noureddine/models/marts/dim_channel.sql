{{ config(materialized='table', schema='gold') }}
WITH channels AS (
    SELECT DISTINCT acquisition_channel AS channel_name
    FROM {{ ref('stg_orders') }}
    WHERE acquisition_channel IS NOT NULL
)
SELECT
    MD5(channel_name)                             AS channel_key,
    channel_name
FROM channels
