{{ config(materialized='table', schema='gold') }}
SELECT
    MD5(calendar_event_id::text)                  AS calendar_event_key,
    calendar_event_id,
    event_name,
    event_type,
    start_date,
    end_date
FROM {{ ref('stg_calendar_events') }}
