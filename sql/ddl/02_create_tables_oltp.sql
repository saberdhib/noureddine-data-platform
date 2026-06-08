-- =============================================================================
-- 02_create_tables_oltp.sql
-- OLTP transactional tables in schema `oltp`.
-- Classification: customers/orders/rag_conversations = C3 (PII/Confidential)
--                 payment fields = C4 (Restricted)
--                 products/inventory/calendar = C2 (Internal)
-- Idempotent: safe to re-run.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Reference / lookup tables (no FKs outward)
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS oltp.categories (
    category_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    category_name   VARCHAR(100) NOT NULL UNIQUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.calendar_events (
    calendar_event_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name        VARCHAR(200) NOT NULL,
    event_type        VARCHAR(100) NOT NULL,  -- e.g. 'religious', 'retail', 'seasonal'
    start_date        DATE         NOT NULL,
    end_date          DATE         NOT NULL,
    CONSTRAINT chk_calendar_dates CHECK (end_date >= start_date)
);

-- ---------------------------------------------------------------------------
-- Core transactional tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS oltp.customers (
    customer_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    email               VARCHAR(320) NOT NULL UNIQUE,         -- C3 PII
    first_name          VARCHAR(100) NOT NULL,                -- C3 PII
    last_name           VARCHAR(100) NOT NULL,                -- C3 PII
    country             VARCHAR(100) NOT NULL DEFAULT 'France',
    city                VARCHAR(100),
    consent_marketing   BOOLEAN     NOT NULL DEFAULT FALSE,
    acquisition_source  VARCHAR(100),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.products (
    product_id      UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    sku             VARCHAR(100)    NOT NULL UNIQUE,
    product_name    VARCHAR(300)    NOT NULL,
    category_id     UUID            NOT NULL REFERENCES oltp.categories(category_id),
    price_eur       NUMERIC(10,2)   NOT NULL CHECK (price_eur >= 0),
    cost_eur        NUMERIC(10,2)   NOT NULL CHECK (cost_eur >= 0),
    seasonality_tag VARCHAR(100),   -- e.g. 'ramadan', 'eid', 'year-round'
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.inventory (
    inventory_id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id          UUID        NOT NULL UNIQUE REFERENCES oltp.products(product_id),
    stock_quantity      INTEGER     NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    reorder_threshold   INTEGER     NOT NULL DEFAULT 10 CHECK (reorder_threshold >= 0),
    last_updated        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.orders (
    order_id            UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID            NOT NULL REFERENCES oltp.customers(customer_id),
    order_date          TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    total_amount        NUMERIC(10,2)   NOT NULL CHECK (total_amount >= 0),
    discount_amount     NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (discount_amount >= 0),
    shipping_cost       NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (shipping_cost >= 0),
    payment_status      VARCHAR(50)     NOT NULL DEFAULT 'pending',  -- C4 Restricted
    order_status        VARCHAR(50)     NOT NULL DEFAULT 'pending',
    acquisition_channel VARCHAR(100),
    created_at          TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.order_items (
    order_item_id   UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id        UUID            NOT NULL REFERENCES oltp.orders(order_id),
    product_id      UUID            NOT NULL REFERENCES oltp.products(product_id),
    quantity        INTEGER         NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(10,2)   NOT NULL CHECK (unit_price >= 0),
    line_total      NUMERIC(10,2)   NOT NULL CHECK (line_total >= 0)
);

CREATE TABLE IF NOT EXISTS oltp.shipments (
    shipment_id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id         UUID        NOT NULL REFERENCES oltp.orders(order_id),
    carrier          VARCHAR(100),
    tracking_number  VARCHAR(200),
    shipping_date    DATE,
    delivery_date    DATE,
    shipment_status  VARCHAR(50) NOT NULL DEFAULT 'pending',
    CONSTRAINT chk_shipment_dates CHECK (delivery_date IS NULL OR delivery_date >= shipping_date)
);

CREATE TABLE IF NOT EXISTS oltp.marketing_events (
    event_id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID        REFERENCES oltp.customers(customer_id),  -- nullable: anonymous
    source              VARCHAR(100) NOT NULL,
    campaign_name       VARCHAR(200),
    event_type          VARCHAR(100) NOT NULL,  -- 'click', 'impression', 'conversion'
    event_timestamp     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS oltp.rag_conversations (
    conversation_id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id             UUID        REFERENCES oltp.customers(customer_id),
    question                TEXT,       -- C3 PII
    intent                  VARCHAR(200),
    conversation_timestamp  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
