-- =============================================================================
-- 04_create_indexes.sql
-- Performance indexes for OLTP and warehouse tables.
-- Idempotent: safe to re-run.
-- =============================================================================

-- OLTP indexes
CREATE INDEX IF NOT EXISTS idx_customers_email
    ON oltp.customers(email);

CREATE INDEX IF NOT EXISTS idx_products_sku
    ON oltp.products(sku);

CREATE INDEX IF NOT EXISTS idx_products_category_id
    ON oltp.products(category_id);

CREATE INDEX IF NOT EXISTS idx_orders_order_date
    ON oltp.orders(order_date);

CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON oltp.orders(customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_order_status
    ON oltp.orders(order_status);

CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON oltp.order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON oltp.order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_shipments_order_id
    ON oltp.shipments(order_id);

CREATE INDEX IF NOT EXISTS idx_marketing_events_customer_id
    ON oltp.marketing_events(customer_id);

CREATE INDEX IF NOT EXISTS idx_marketing_events_event_timestamp
    ON oltp.marketing_events(event_timestamp);

CREATE INDEX IF NOT EXISTS idx_rag_conversations_customer_id
    ON oltp.rag_conversations(customer_id);

CREATE INDEX IF NOT EXISTS idx_inventory_product_id
    ON oltp.inventory(product_id);

-- Warehouse indexes
CREATE INDEX IF NOT EXISTS idx_fact_sales_customer_key
    ON gold.fact_sales(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_product_key
    ON gold.fact_sales(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date_key
    ON gold.fact_sales(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_channel_key
    ON gold.fact_sales(channel_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_calendar_event_key
    ON gold.fact_sales(calendar_event_key);

CREATE INDEX IF NOT EXISTS idx_fact_sales_order_id
    ON gold.fact_sales(order_id);

CREATE INDEX IF NOT EXISTS idx_dim_customer_customer_id
    ON gold.dim_customer(customer_id);

CREATE INDEX IF NOT EXISTS idx_dim_product_sku
    ON gold.dim_product(sku);

CREATE INDEX IF NOT EXISTS idx_dim_date_date
    ON gold.dim_date(date);
