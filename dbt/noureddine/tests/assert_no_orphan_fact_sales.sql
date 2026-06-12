-- Fails if any fact_sales row is missing a customer_key (orphan).
SELECT sale_key
FROM {{ ref('fact_sales') }}
WHERE customer_key IS NULL
