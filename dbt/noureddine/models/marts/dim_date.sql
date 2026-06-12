{{ config(materialized='table', schema='gold') }}
WITH dates AS (
    SELECT generate_series(
        '2023-01-01'::date,
        '2027-12-31'::date,
        '1 day'::interval
    )::date AS date
)
SELECT
    TO_CHAR(date, 'YYYYMMDD')::integer            AS date_key,
    date,
    EXTRACT(DAY     FROM date)::integer            AS day,
    EXTRACT(WEEK    FROM date)::integer            AS week,
    EXTRACT(MONTH   FROM date)::integer            AS month,
    EXTRACT(QUARTER FROM date)::integer            AS quarter,
    EXTRACT(YEAR    FROM date)::integer            AS year,
    EXTRACT(DOW     FROM date) IN (0, 6)           AS is_weekend
FROM dates
