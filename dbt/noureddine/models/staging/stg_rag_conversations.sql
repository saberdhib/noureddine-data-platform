{{ config(materialized='view') }}
SELECT
    conversation_id::uuid      AS conversation_id,
    customer_id::uuid          AS customer_id,
    question,
    intent,
    conversation_timestamp
FROM {{ source('oltp', 'rag_conversations') }}
