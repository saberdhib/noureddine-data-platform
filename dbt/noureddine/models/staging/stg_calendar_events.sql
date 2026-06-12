{{ config(materialized='view') }}
SELECT
    calendar_event_id::uuid    AS calendar_event_id,
    event_name,
    event_type,
    start_date,
    end_date
FROM {{ source('oltp', 'calendar_events') }}
