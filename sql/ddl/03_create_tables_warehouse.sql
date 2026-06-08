-- =============================================================================
-- 03_create_tables_warehouse.sql
-- Analytical star schema in schema `gold`.
-- Surrogate keys: BIGINT GENERATED ALWAYS AS IDENTITY.
-- Natural / source keys kept for traceability.
-- Idempotent: safe to re-run.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Dimension tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold.dim_customer (
    customer_key        BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id         UUID        NOT NULL,           -- source natural key
    country             VARCHAR(100),
    city                VARCHAR(100),
    segment             VARCHAR(100),                   -- e.g. 'loyal', 'new', 'at-risk'
    acquisition_source  VARCHAR(100),
    valid_from          DATE        NOT NULL DEFAULT CURRENT_DATE,
    valid_to            DATE
);

CREATE TABLE IF NOT EXISTS gold.dim_product (
    product_key     BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id      UUID        NOT NULL,               -- source natural key
    sku             VARCHAR(100) NOT NULL,
    product_name    VARCHAR(300) NOT NULL,
    category        VARCHAR(100),
    seasonality_tag VARCHAR(100),
    valid_from      DATE        NOT NULL DEFAULT CURRENT_DATE,
    valid_to        DATE
);

CREATE TABLE IF NOT EXISTS gold.dim_date (
    date_key    BIGINT  GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    date        DATE    NOT NULL UNIQUE,
    day         SMALLINT NOT NULL,
    week        SMALLINT NOT NULL,
    month       SMALLINT NOT NULL,
    quarter     SMALLINT NOT NULL,
    year        SMALLINT NOT NULL,
    is_weekend  BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS gold.dim_channel (
    channel_key     BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    channel_name    VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS gold.dim_calendar_event (
    calendar_event_key  BIGINT      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    calendar_event_id   UUID        NOT NULL,           -- source natural key
    event_name          VARCHAR(200) NOT NULL,
    event_type          VARCHAR(100) NOT NULL
);

-- ---------------------------------------------------------------------------
-- Fact table
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS gold.fact_sales (
    sale_key            BIGINT          GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id            UUID            NOT NULL,
    order_item_id       UUID,
    customer_key        BIGINT          NOT NULL REFERENCES gold.dim_customer(customer_key),
    product_key         BIGINT          NOT NULL REFERENCES gold.dim_product(product_key),
    date_key            BIGINT          NOT NULL REFERENCES gold.dim_date(date_key),
    channel_key         BIGINT          NOT NULL REFERENCES gold.dim_channel(channel_key),
    calendar_event_key  BIGINT          REFERENCES gold.dim_calendar_event(calendar_event_key),
    quantity            INTEGER         NOT NULL CHECK (quantity > 0),
    revenue             NUMERIC(10,2)   NOT NULL CHECK (revenue >= 0),
    discount            NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (discount >= 0),
    shipping_cost       NUMERIC(10,2)   NOT NULL DEFAULT 0 CHECK (shipping_cost >= 0),
    margin              NUMERIC(10,2)
);
