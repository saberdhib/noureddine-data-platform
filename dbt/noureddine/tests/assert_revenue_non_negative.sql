-- Fails if any sale has negative revenue.
SELECT sale_key, revenue
FROM {{ ref('fact_sales') }}
WHERE revenue < 0
