{{ config(materialized='view') }}
SELECT
    shipment_id::uuid          AS shipment_id,
    order_id::uuid             AS order_id,
    carrier,
    tracking_number,
    shipping_date,
    delivery_date,
    shipment_status
FROM {{ source('oltp', 'shipments') }}
