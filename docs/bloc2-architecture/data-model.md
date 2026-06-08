# Data Model — NOUREDDINE Data Platform

## 1. OLTP Transactional Model (schema `oltp`)

### Entity Relationship Diagram

See `diagrams/erd.mmd` for the Mermaid ERD source.

### Table descriptions

| Table | PK | Key FKs | Governance | Description |
|-------|-----|---------|------------|-------------|
| `categories` | category_id (UUID) | — | C2 Internal | Product categories: Grooming, RTW, Accessories, GiftSet, Leather |
| `products` | product_id (UUID) | category_id | C2 Internal | SKU catalogue with price, cost, seasonality tag |
| `inventory` | inventory_id (UUID) | product_id (UNIQUE) | C2 Internal | Stock levels and reorder thresholds per product |
| `customers` | customer_id (UUID) | — | **C3 Confidential** | Customer PII: email, name, country, city, marketing consent |
| `orders` | order_id (UUID) | customer_id | **C3/C4** | Order header: amount, discount, shipping, payment status |
| `order_items` | order_item_id (UUID) | order_id, product_id | C2 Internal | Line items: qty, unit price, line total |
| `shipments` | shipment_id (UUID) | order_id | C2 Internal | Carrier, tracking, shipping/delivery dates |
| `marketing_events` | event_id (UUID) | customer_id (nullable) | C3 Confidential | Clicks, impressions, conversions by channel |
| `rag_conversations` | conversation_id (UUID) | customer_id (nullable) | **C3 Confidential** | Customer questions and intents from the RAG assistant |
| `calendar_events` | calendar_event_id (UUID) | — | C2 Internal | Islamic + retail calendar: Ramadan, Eid, Nikah, Black Friday |

### Relationships

```
customers ──< orders ──< order_items >── products >── categories
                    └──< shipments              └──< inventory
customers ──< marketing_events
customers ──< rag_conversations
calendar_events (referenced by star schema)
```

### Governance classification key

| Class | Label | Examples |
|-------|-------|---------|
| C1 | Public | Published product names, prices |
| C2 | Internal | Categories, inventory levels, logistics |
| C3 | Confidential (PII) | Customer name/email, RAG questions |
| C4 | Restricted | Payment status, payment method |

---

## 2. Analytical Star Schema (schema `gold`)

### Grain

One row in `fact_sales` = **one order line item** (one product within one order).

This grain allows:
- Revenue and margin analysis at product level
- Attribution by acquisition channel, calendar event
- Customer-level aggregation by joining to `dim_customer`

### Star schema diagram

See `diagrams/star-schema.mmd`.

### Dimension tables

| Dimension | Surrogate key | Natural key | Key attributes |
|-----------|--------------|-------------|----------------|
| `dim_customer` | customer_key (BIGINT IDENTITY) | customer_id (UUID) | country, city, segment, acquisition_source |
| `dim_product` | product_key (BIGINT IDENTITY) | product_id (UUID) | sku, product_name, category, seasonality_tag |
| `dim_date` | date_key (BIGINT IDENTITY) | date (DATE UNIQUE) | day, week, month, quarter, year, is_weekend |
| `dim_channel` | channel_key (BIGINT IDENTITY) | channel_name (UNIQUE) | channel_name |
| `dim_calendar_event` | calendar_event_key (BIGINT IDENTITY) | calendar_event_id (UUID) | event_name, event_type |

### Fact table: `fact_sales`

| Column | Type | Description |
|--------|------|-------------|
| sale_key | BIGINT IDENTITY | Surrogate PK |
| order_id | UUID | Traceability back to OLTP |
| order_item_id | UUID | Traceability back to OLTP |
| customer_key | BIGINT FK | → dim_customer |
| product_key | BIGINT FK | → dim_product |
| date_key | BIGINT FK | → dim_date (order date) |
| channel_key | BIGINT FK | → dim_channel |
| calendar_event_key | BIGINT FK (nullable) | → dim_calendar_event (if order falls within event window) |
| quantity | INTEGER | Units sold |
| revenue | NUMERIC(10,2) | Line total (unit_price × qty) |
| discount | NUMERIC(10,2) | Order-level discount allocated to line |
| shipping_cost | NUMERIC(10,2) | Order-level shipping |
| margin | NUMERIC(10,2) | revenue − (cost × qty) |

### Analytical views

| View | Description |
|------|-------------|
| `gold.v_daily_revenue` | Revenue, margin, order count, units sold by day |
| `gold.v_sales_by_calendar_event` | Revenue and margin grouped by Islamic/retail event |
| `gold.v_top_products` | Products ranked by total revenue |

---

## 3. Seasonality & Business Context

The `seasonality_tag` field on products and `calendar_event_key` in `fact_sales` are the **core analytics hooks** for the brand's demand forecasting challenge:

- Products tagged `ramadan` see 3–5× normal sales velocity during Ramadan.
- Products tagged `eid` peak in the 3 days around Eid al-Fitr and Eid al-Adha.
- Products tagged `nikah` peak May–July (nikah ceremony season in France).
- `year-round` products provide the baseline.

The `fact_sales.calendar_event_key` is populated by a lookup: if the order date falls within any calendar event window, the row is tagged. Orders outside any event window have `NULL` calendar_event_key.
