# NOUREDDINE — Data Asset Catalogue (v2)

> Auto-generated from the dbt model governance annotations (`meta` blocks) by `scripts/export_governance_catalogue.py`. Do not edit by hand — re-run the script.

_Generated: 2026-06-12 · 19 models._

Classification scheme (Bloc 1): **C1** Public · **C2** Internal · **C3** Confidential (PII) · **C4** Restricted. PII levels: `none` · `indirect` · `direct`.

## Summary

| Model | Layer | Classification | PII level | Retention (days) |
|---|---|---|---|---|
| `stg_calendar_events` | silver | C2 | none | 3650 |
| `stg_categories` | silver | C2 | none | 3650 |
| `stg_customers` | silver | C3 | direct | 1825 |
| `stg_inventory` | silver | C2 | none | 3650 |
| `stg_marketing_events` | silver | C3 | indirect | 1095 |
| `stg_order_items` | silver | C3 | indirect | 1825 |
| `stg_orders` | silver | C3 | indirect | 1825 |
| `stg_products` | silver | C2 | none | 3650 |
| `stg_rag_conversations` | silver | C3 | indirect | 1095 |
| `stg_shipments` | silver | C3 | indirect | 1825 |
| `dim_calendar_event` | gold | C2 | none | 3650 |
| `dim_channel` | gold | C2 | none | 3650 |
| `dim_customer` | gold | C3 | indirect | 1825 |
| `dim_date` | gold | C2 | none | 3650 |
| `dim_product` | gold | C2 | none | 3650 |
| `fact_sales` | gold | C2 | indirect | 1825 |
| `v_daily_revenue` | gold | C2 | none | 3650 |
| `v_sales_by_calendar_event` | gold | C2 | none | 3650 |
| `v_top_products` | gold | C2 | none | 3650 |

## Model detail

### `stg_calendar_events`

_Cleaned Islamic + retail calendar events (silver). No personal data = C2._

- **Layer:** silver
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.calendar_events
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `calendar_event_id` | false | none | C2 | Unique identifier of a calendar event. | — |
| `event_name` | false | none | C2 | Name of the Islamic or retail calendar event. | — |
| `event_type` | false | none | C2 | Family of the event (e.g. religious, retail). | — |
| `start_date` | false | none | C2 | First day of the event window. | — |
| `end_date` | false | none | C2 | Last day of the event window. | — |

### `stg_categories`

_Cleaned product categories (silver). No personal data = C2._

- **Layer:** silver
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.categories
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `category_id` | false | none | C2 | Unique identifier of a product category. | — |
| `category_name` | false | none | C2 | Name of the product category (e.g. Qamis, Grooming). | — |
| `created_at` | false | none | C2 | Timestamp the category record was created. | — |

### `stg_customers`

_Cleaned customer records (silver). Direct PII = C3._

- **Layer:** silver
- **Classification:** C3
- **PII level:** direct
- **Retention (days):** 1825
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.customers
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `customer_id` | true | identifier | C3 | Unique identifier of an individual customer. | — |
| `email` | true | contact | C3 | Customer email used for order and marketing communication. | — |
| `first_name` | true | contact | C3 | Given name of the customer. | — |
| `last_name` | true | contact | C3 | Family name of the customer. | — |
| `country` | false | none | C2 | ISO country of the customer (market segmentation). | — |
| `city` | false | none | C2 | City of the customer. | — |
| `consent_marketing` | false | none | C2 | Whether the customer consented to marketing communication. | — |
| `acquisition_source` | false | none | C2 | Marketing source that first acquired the customer. | — |
| `created_at` | false | none | C2 | Timestamp the customer record was created. | — |
| `updated_at` | false | none | C2 | Timestamp the customer record was last updated. | — |

### `stg_inventory`

_Cleaned inventory levels (silver). No personal data = C2._

- **Layer:** silver
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.inventory
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `inventory_id` | false | none | C2 | Unique identifier of an inventory record. | — |
| `product_id` | false | none | C2 | Product the inventory level refers to. | — |
| `stock_quantity` | false | none | C2 | Units of the product currently in stock. | — |
| `reorder_threshold` | false | none | C2 | Stock level at which the product should be restocked. | — |
| `last_updated` | false | none | C2 | Timestamp the inventory record was last updated. | — |

### `stg_marketing_events`

_Cleaned marketing engagement events (silver). Indirect PII via customer_id = C3._

- **Layer:** silver
- **Classification:** C3
- **PII level:** indirect
- **Retention (days):** 1095
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.marketing_events
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `event_id` | false | none | C2 | Unique identifier of a marketing event. | — |
| `customer_id` | true | identifier | C3 | Customer associated with the marketing event (indirect personal link). | — |
| `source` | false | none | C2 | Channel the marketing event originated from. | — |
| `campaign_name` | false | none | C2 | Name of the marketing campaign. | — |
| `event_type` | false | none | C2 | Type of marketing event (e.g. click, impression). | — |
| `event_timestamp` | false | none | C2 | Timestamp of the marketing event. | — |

### `stg_order_items`

_Cleaned order line items (silver). Indirect PII via parent order = C3._

- **Layer:** silver
- **Classification:** C3
- **PII level:** indirect
- **Retention (days):** 1825
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.order_items
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `order_item_id` | false | none | C2 | Unique identifier of an order line item. | — |
| `order_id` | false | none | C2 | Order the line item belongs to. | — |
| `product_id` | false | none | C2 | Product sold on this line item. | — |
| `quantity` | false | none | C2 | Quantity of the product ordered on this line. | — |
| `unit_price` | false | financial | C2 | Price per unit of the product in EUR at order time. | — |
| `line_total` | false | financial | C2 | Total value of the line (quantity x unit_price) in EUR. | — |

### `stg_orders`

_Cleaned orders (silver). Indirect PII via customer_id = C3._

- **Layer:** silver
- **Classification:** C3
- **PII level:** indirect
- **Retention (days):** 1825
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.orders
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `order_id` | false | none | C2 | Unique identifier of a customer order. | — |
| `customer_id` | true | identifier | C3 | Customer who placed the order (indirect personal link). | — |
| `order_date` | false | none | C2 | Date and time the order was placed. | — |
| `order_day` | false | none | C2 | Calendar day of the order, used to join the date dimension. | order_date cast to date. |
| `total_amount` | false | financial | C2 | Gross monetary value of the order in EUR. | — |
| `discount_amount` | false | financial | C2 | Total discount applied to the order in EUR. | — |
| `shipping_cost` | false | financial | C2 | Shipping fee billed on the order in EUR. | — |
| `payment_status` | false | none | C2 | Payment state of the order (paid/pending/refunded). No card data stored. | — |
| `order_status` | false | none | C2 | Fulfilment state of the order. | — |
| `acquisition_channel` | false | none | C2 | Channel that drove the order, defaulted to 'direct'. | COALESCE(acquisition_channel, 'direct'). |
| `created_at` | false | none | C2 | Timestamp the order record was created. | — |

### `stg_products`

_Cleaned product catalogue (silver). No personal data = C2._

- **Layer:** silver
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.products
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `product_id` | false | none | C2 | Unique identifier of a product. | — |
| `sku` | false | none | C2 | Unique stock-keeping code of the product. | — |
| `product_name` | false | none | C2 | Commercial name of the product. | — |
| `category_id` | false | none | C2 | Category the product belongs to. | — |
| `price_eur` | false | financial | C2 | Catalogue selling price of the product in EUR. | — |
| `cost_eur` | false | financial | C2 | Unit cost of the product in EUR. | — |
| `seasonality_tag` | false | none | C2 | Seasonal demand tag tied to the Islamic/retail calendar. | — |
| `created_at` | false | none | C2 | Timestamp the product record was created. | — |
| `updated_at` | false | none | C2 | Timestamp the product record was last updated. | — |

### `stg_rag_conversations`

_Cleaned RAG assistant conversations (silver). Free-text + customer link = C3._

- **Layer:** silver
- **Classification:** C3
- **PII level:** indirect
- **Retention (days):** 1095
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.rag_conversations
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `conversation_id` | false | none | C2 | Unique identifier of a RAG conversation. | — |
| `customer_id` | true | identifier | C3 | Customer who engaged the RAG assistant (indirect personal link). | — |
| `question` | true | behavioral | C3 | Free-text question the customer asked the assistant; may reveal personal preferences. | — |
| `intent` | false | none | C2 | Derived intent label of the conversation. | — |
| `conversation_timestamp` | false | none | C2 | Timestamp of the RAG conversation. | — |

### `stg_shipments`

_Cleaned shipments (silver). Indirect PII via parent order = C3._

- **Layer:** silver
- **Classification:** C3
- **PII level:** indirect
- **Retention (days):** 1825
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.shipments
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/staging/_staging.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `shipment_id` | false | none | C2 | Unique identifier of a shipment. | — |
| `order_id` | false | none | C2 | Order being shipped. | — |
| `carrier` | false | none | C2 | Carrier handling the shipment. | — |
| `tracking_number` | true | identifier | C3 | Carrier tracking number that can be linked back to a customer's order. | — |
| `shipping_date` | false | none | C2 | Date the order was dispatched. | — |
| `delivery_date` | false | none | C2 | Date the order was delivered. | — |
| `shipment_status` | false | none | C2 | Current state of the shipment. | — |

### `dim_calendar_event`

_Islamic + retail calendar event dimension (gold). No personal data = C2._

- **Layer:** gold
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.calendar_events
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `calendar_event_key` | false | none | C2 | Hashed surrogate key joining facts to the calendar-event dimension. | MD5(calendar_event_id::text). |
| `calendar_event_id` | false | none | C2 | Unique identifier of a calendar event. | — |
| `event_name` | false | none | C2 | Name of the Islamic or retail calendar event. | — |
| `event_type` | false | none | C2 | Family of the event (e.g. religious, retail). | — |
| `start_date` | false | none | C2 | First day of the event window. | — |
| `end_date` | false | none | C2 | Last day of the event window. | — |

### `dim_channel`

_Acquisition channel dimension (gold). No personal data = C2._

- **Layer:** gold
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.orders
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `channel_key` | false | none | C2 | Hashed surrogate key joining facts to the channel dimension. | MD5(channel_name). |
| `channel_name` | false | none | C2 | Distinct acquisition channel that drove orders. | — |

### `dim_customer`

_Customer dimension (gold). Customer-level keys, no raw email exposed = indirect PII = C3._

- **Layer:** gold
- **Classification:** C3
- **PII level:** indirect
- **Retention (days):** 1825
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.customers
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `customer_key` | false | none | C2 | Hashed surrogate key joining facts to the customer dimension. | MD5(customer_id::text). |
| `customer_id` | true | identifier | C3 | Unique identifier of an individual customer (indirect personal link). | — |
| `country` | false | none | C2 | ISO country of the customer (market segmentation). | — |
| `city` | false | none | C2 | City of the customer. | — |
| `segment` | false | none | C2 | Customer segment ('engaged' vs 'standard') derived from marketing consent. | CASE WHEN consent_marketing THEN 'engaged' ELSE 'standard' END. |
| `acquisition_source` | false | none | C2 | Marketing source that first acquired the customer. | — |

### `dim_date`

_Date spine 2023-01-01 -> 2027-12-31 (gold). No personal data = C2._

- **Layer:** gold
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** generated
- **Update frequency:** static
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `date_key` | false | none | C2 | Integer date key in YYYYMMDD form. | TO_CHAR(date, 'YYYYMMDD')::integer. |
| `date` | false | none | C2 | Calendar date of the row. | — |
| `day` | false | none | C2 | Day of the month (1-31). | EXTRACT(DAY FROM date). |
| `week` | false | none | C2 | ISO week number of the year. | EXTRACT(WEEK FROM date). |
| `month` | false | none | C2 | Month of the year (1-12). | EXTRACT(MONTH FROM date). |
| `quarter` | false | none | C2 | Calendar quarter (1-4). | EXTRACT(QUARTER FROM date). |
| `year` | false | none | C2 | Calendar year. | EXTRACT(YEAR FROM date). |
| `is_weekend` | false | none | C2 | True if the date is Saturday or Sunday. | EXTRACT(DOW FROM date) IN (0, 6). |

### `dim_product`

_Product dimension (gold). No personal data = C2._

- **Layer:** gold
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.products, oltp.categories
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `product_key` | false | none | C2 | Hashed surrogate key joining facts to the product dimension. | MD5(product_id::text). |
| `product_id` | false | none | C2 | Unique identifier of a product. | — |
| `sku` | false | none | C2 | Unique stock-keeping code of the product. | — |
| `product_name` | false | none | C2 | Commercial name of the product. | — |
| `category` | false | none | C2 | Category the product belongs to (e.g. Qamis, Grooming). | Joined from stg_categories.category_name on category_id. |
| `seasonality_tag` | false | none | C2 | Seasonal demand tag tied to the Islamic/retail calendar. | — |

### `fact_sales`

_Sales fact at order_item grain (gold). Owned by dbt from Bloc 3. Carries customer_key = indirect PII = C3 model, body aggregate/keys._

- **Layer:** gold
- **Classification:** C2
- **PII level:** indirect
- **Retention (days):** 1825
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** oltp.orders, oltp.order_items
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `sale_key` | false | none | C2 | Hashed surrogate key of an order-item sale line. | MD5(order_item_id::text). |
| `order_id` | false | none | C2 | Order the sale line belongs to. | — |
| `customer_key` | true | identifier | C3 | Customer who placed the order (indirect personal link via hashed key). | — |
| `product_key` | false | none | C2 | Product sold on this line. | — |
| `date_key` | false | none | C2 | Order day of the sale line. | — |
| `channel_key` | false | none | C2 | Acquisition channel of the sale line. | — |
| `calendar_event_key` | false | none | C2 | Calendar event active on the order day (smallest window wins). | — |
| `quantity` | false | none | C2 | Quantity of the product sold on this line. | — |
| `revenue` | false | financial | C2 | Revenue of the sale line in EUR. | oi.line_total. |
| `discount` | false | financial | C2 | Order-level discount allocated to the line in proportion to its value. | COALESCE(o.discount_amount / NULLIF(o.total_amount, 0) * oi.line_total, 0). |
| `shipping_cost` | false | financial | C2 | Order-level shipping cost split evenly across the order's lines. | COALESCE(o.shipping_cost / NULLIF(lpo.n_lines, 0), 0). |
| `margin` | false | financial | C2 | Gross margin of the line in EUR assuming 60% cost of goods. | oi.line_total - (oi.unit_price * oi.quantity * 0.6). |

### `v_daily_revenue`

_Daily revenue / margin aggregate view (gold). Aggregate, no PII = C2._

- **Layer:** gold
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** gold.fact_sales, gold.dim_date
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `date` | false | none | C2 | Day the revenue was recognised. | — |
| `year` | false | none | C2 | Calendar year of the day. | — |
| `month` | false | none | C2 | Calendar month of the day. | — |
| `week` | false | none | C2 | ISO week number of the day. | — |
| `total_revenue` | false | financial | C2 | Total revenue recognised on the day in EUR. | SUM(fact_sales.revenue) grouped by day. |
| `total_discount` | false | financial | C2 | Total discount allocated on the day in EUR. | SUM(fact_sales.discount) grouped by day. |
| `total_shipping` | false | financial | C2 | Total shipping cost on the day in EUR. | SUM(fact_sales.shipping_cost) grouped by day. |
| `total_margin` | false | financial | C2 | Total gross margin on the day in EUR. | SUM(fact_sales.margin) grouped by day. |
| `order_count` | false | none | C2 | Number of distinct orders on the day. | COUNT(DISTINCT fact_sales.order_id) grouped by day. |
| `units_sold` | false | none | C2 | Total units sold on the day. | SUM(fact_sales.quantity) grouped by day. |

### `v_sales_by_calendar_event`

_Revenue by Islamic + retail calendar event view (gold). Aggregate, no PII = C2._

- **Layer:** gold
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** gold.fact_sales, gold.dim_calendar_event, gold.dim_date
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `event_name` | false | none | C2 | Name of the calendar event the sales are attributed to. | — |
| `event_type` | false | none | C2 | Family of the calendar event (e.g. religious, retail). | — |
| `year` | false | none | C2 | Calendar year of the aggregated sales. | — |
| `total_revenue` | false | financial | C2 | Total revenue attributed to the event in the year in EUR. | SUM(fact_sales.revenue) grouped by event and year. |
| `total_discount` | false | financial | C2 | Total discount attributed to the event in the year in EUR. | SUM(fact_sales.discount) grouped by event and year. |
| `total_margin` | false | financial | C2 | Total gross margin attributed to the event in the year in EUR. | SUM(fact_sales.margin) grouped by event and year. |
| `order_count` | false | none | C2 | Number of distinct orders attributed to the event in the year. | COUNT(DISTINCT fact_sales.order_id) grouped by event and year. |
| `units_sold` | false | none | C2 | Total units sold attributed to the event in the year. | SUM(fact_sales.quantity) grouped by event and year. |
| `avg_unit_revenue` | false | financial | C2 | Average revenue per unit sold for the event in the year in EUR. | ROUND(AVG(fact_sales.revenue / NULLIF(fact_sales.quantity, 0)), 2). |

### `v_top_products`

_Top products by revenue view (gold). Aggregate, no PII = C2._

- **Layer:** gold
- **Classification:** C2
- **PII level:** none
- **Retention (days):** 3650
- **Owner role:** Head of Operations
- **Steward role:** Data Steward — Commerce
- **Source systems:** gold.fact_sales, gold.dim_product
- **Update frequency:** micro_batch_10min
- **Defined in:** `dbt/noureddine/models/marts/_marts.yml`

| Column | PII | PII category | Classification | Business definition | Transformation |
|---|---|---|---|---|---|
| `sku` | false | none | C2 | Stock-keeping code of the product. | — |
| `product_name` | false | none | C2 | Commercial name of the product. | — |
| `category` | false | none | C2 | Category the product belongs to. | — |
| `seasonality_tag` | false | none | C2 | Seasonal demand tag of the product. | — |
| `total_revenue` | false | financial | C2 | Total revenue generated by the product in EUR. | SUM(fact_sales.revenue) grouped by product. |
| `units_sold` | false | none | C2 | Total units of the product sold. | SUM(fact_sales.quantity) grouped by product. |
| `order_count` | false | none | C2 | Number of distinct orders that contained the product. | COUNT(DISTINCT fact_sales.order_id) grouped by product. |

