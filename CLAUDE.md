# CLAUDE.md — NOUREDDINE Data Platform

> Permanent project context for Claude Code.
> Read this file fully before any task. It defines the business, the architecture, the conventions, and the repository structure for the **entire** PFE (Blocs 1 → 4).
> When in doubt, follow this file over any other assumption.

---

## 1. Project Identity

**Project name:** NOUREDDINE Data Platform
**Type:** End-of-study project (PFE) — RNCP certification, Data Engineering / Data Architecture track
**Owner:** Single student developer
**Working language of code & docs:** English (code, comments, READMEs). Business/governance docs may be French.

**What this is:** A complete, reproducible, end-to-end data platform for a fictional (but realistically modelled) premium e-commerce brand. The platform ingests simulated e-commerce data, stores it in a layered warehouse, transforms it, trains a sales-forecasting model, serves predictions via an API, and monitors everything.

The PFE is split into **4 Blocs**, delivered sequentially in **one mono-repo**:

| Bloc | Theme | Status |
|------|-------|--------|
| Bloc 1 | Data Governance (policy, RGPD, RACI, risks) | ✅ Done (Word + PPTX, in `/docs/bloc1`) |
| Bloc 2 | Data Architecture (infra, warehouse schema, Docker) | 🟢 **CURRENT** |
| Bloc 3 | Data Pipelines (Airflow DAGs, dbt, data quality) | ⏳ Next |
| Bloc 4 | AI / MLOps (forecasting model, FastAPI, CI/CD, Evidently) | ⏳ After |

**Critical rule:** Build only the current Bloc's scope. Do NOT pre-build later Blocs. Leave clean, empty, well-named placeholders for future Blocs so the structure is ready but not filled.

---

## 2. Business Context — NOUREDDINE

NOUREDDINE is a premium direct-to-consumer (D2C) menswear e-commerce brand serving the Western Muslim diaspora.

- **Revenue:** ~€8–9M/year · **Team:** ~30 people · **Age:** 4–5 years old, operational and profitable.
- **Market:** France (Paris first) → UK → Germany → Benelux.
- **Customers:** Muslim men, CSP+ (higher socio-professional category), 20–47 years old.
- **Products:** grooming (siwak, beard oil ~€45), ready-to-wear (qamis, polo, trousers, suits, t-shirts up to €450), accessories, leather goods, gift sets.
- **Average order value:** €80–150 (excl. gift sets).
- **Tech (real, current):** Headless site (Next.js + Shopify) for catalogue, stock, cart, shipping labels, tracking. Acquisition via Instagram/TikTok/ads/affiliate/QR/web & AI search. A RAG shopping assistant (style advice, questionnaire, photo upload, virtual try-on).

### Customer & data journey (the real-world process we model)
1. User arrives from: website / QR code / affiliate link / social / paid ad / web or AI search (ChatGPT, Claude, Gemini).
2. Lands on the Shopify-powered site (stock, products, delivery notes, shipping price, cart, tracking).
3. Engages a **RAG assistant**: style guidance, questionnaire or uploaded photo, virtual model preview.
4. Talks to the RAG, buys a product.
5. Order hits the **back office**: staff scan the product, register it under the customer with a special code, send to shipping.
6. Customer is recorded in the registry with their purchase; automated confirmation + tracking emails are sent.
7. Post-sale: identify the customer, communicate, propose the app / socials / site with personalised advice & new arrivals.
8. Analyse: what was asked to the RAG, what interests customers most, which product they went to first, how to improve the site.
9. Operations: manage products sold, footfall, staff workload, stock forecasting, communications, demand forecasting, alerts (site down, stock-out, trend, fraud, social trend analysis), SAV (customer service).

### Core business problem the platform solves
Piloting a **limited stock against irregular, event-driven demand**. Demand is highly seasonal around the **Islamic cultural calendar** (Ramadan, Eid al-Fitr, Eid al-Adha) and life events (Nikah season), plus retail peaks (Black Friday, Summer Sale). Without governed data and forecasting, the brand risks stock-outs on limited drops and poor cash/stock planning.

### Target end-state (vision — full platform across all Blocs)
Data collected from everywhere → ingested into a **Data Warehouse** → processed into an **all-view performance dashboard** (sales, forecasting) → an **MLOps** layer that adjusts treasury/stock forecasts → communication agents → monitoring, alerting, and metric-improvement pipelines (e.g. alert if the dashboard fails to refresh because of data issues).

---

## 3. Architecture Principles (apply to every Bloc)

1. **Medallion architecture**: Bronze (raw) → Silver (cleaned, typed, quality-validated) → Gold (business metrics, ML-ready features).
2. **Zero-licence, near-zero-cost**: only free/open-source tools. No paid cloud services. Must run on a laptop via Docker Compose.
3. **Reproducibility first**: anyone clones the repo, runs one documented command, and the whole stack comes up. Docker mandatory.
4. **Governed by Bloc 1**: the data model, classifications (C1–C4), policies (P-01→P-04), and quality dimensions (DAMA) defined in Bloc 1 govern technical choices here. Customer PII is C3, payment data is C4.
5. **Separation of concerns**: storage, orchestration, transformation, serving, and monitoring are distinct, swappable services.
6. **Everything documented**: each top-level folder has purpose; the root README explains how to run and verify.

---

## 4. Technology Stack (locked)

| Layer | Tool | Notes |
|-------|------|-------|
| Object storage (Data Lake) | **MinIO** (S3-compatible) | Local, zero-cost. Same API as AWS S3. Migration-to-S3 documented, not implemented. |
| Warehouse / OLTP + OLAP | **PostgreSQL 16** | Holds OLTP transactional tables + analytical star schema. |
| Orchestration | **Apache Airflow** | Bloc 2: service runs, with an empty `/dags` skeleton. Logic comes in Bloc 3. |
| Transformation | **dbt** (dbt-postgres) | Bloc 2: project skeleton only (folders, profiles). Models come in Bloc 3. |
| DB admin / observability | **pgAdmin** + Docker **health-checks** | Visual DB browsing + container self-monitoring. |
| Serving (API) | **FastAPI** | Bloc 4. Bloc 2: leave an empty `/api` placeholder. |
| ML monitoring | **Evidently** | Bloc 4. Not in Bloc 2. |
| CI/CD | **GitHub Actions** | Bloc 4 (full). Bloc 2: a minimal lint/validate workflow is acceptable. |
| Versioning | **Git + GitHub** | Mono-repo. |
| Containerisation | **Docker + Docker Compose** | Mandatory. The whole stack is brought up with Compose. |

**Explicitly excluded:** Kubernetes, Terraform (optional and not used — justify in docs as disproportionate for this scale), any paid SaaS, Kafka/Kinesis (no real streaming in this PFE; batch only).

**Cloud talking point:** MinIO is used so the architecture is S3-native (S3 API) while remaining free and laptop-runnable. The README documents how it maps 1:1 to AWS S3 for a real deployment.

---

## 5. Repository Structure (mono-repo — the ONE true layout)

This is the canonical structure for the **entire** project. In Bloc 2, create the full tree but only fill the Bloc 2 parts. Leave `.gitkeep` files and short `README.md` stubs in folders reserved for later Blocs.

```
noureddine-data-platform/
├── README.md                      # Root: project overview, how to run, verify, architecture summary
├── CLAUDE.md                      # This file (project context)
├── .gitignore
├── .env.example                   # All env vars, documented, no secrets
├── LICENSE
│
├── docs/                          # All documentation & deliverables
│   ├── bloc1-governance/          # Bloc 1 deliverables (Word/PPTX live here)
│   │   └── README.md              # stub: "See governance plan documents"
│   ├── bloc2-architecture/        # Bloc 2 docs: architecture, decisions, diagrams
│   │   ├── README.md
│   │   ├── architecture.md        # logical + technical architecture write-up
│   │   ├── data-model.md          # MCD/ERD + star schema explanation
│   │   ├── adr/                   # Architecture Decision Records (one .md per decision)
│   │   └── diagrams/              # Mermaid sources (.mmd) + exported .png/.svg
│   ├── bloc3-pipelines/           # stub for now
│   │   └── README.md
│   └── bloc4-mlops/               # stub for now
│       └── README.md
│
├── infra/                         # Infrastructure-as-config (Docker)
│   ├── docker-compose.yml         # The full local stack
│   ├── postgres/
│   │   └── init/                  # SQL run automatically on first DB boot (symlink/copy of sql/ddl + seed)
│   ├── minio/
│   │   └── README.md              # bucket bootstrap notes
│   ├── pgadmin/
│   │   └── servers.json           # pre-registered PostgreSQL connection
│   ├── airflow/
│   │   └── README.md              # how the airflow service is wired (skeleton in Bloc 2)
│   └── scripts/
│       ├── up.sh                  # bring stack up
│       ├── down.sh                # tear down
│       └── healthcheck.sh         # verify all services healthy + tables present
│
├── sql/                           # Database definition (Bloc 2 core)
│   ├── ddl/
│   │   ├── 01_create_schemas.sql  # bronze / silver / gold / oltp schemas
│   │   ├── 02_create_tables_oltp.sql
│   │   ├── 03_create_tables_warehouse.sql
│   │   ├── 04_create_indexes.sql
│   │   └── 05_create_views.sql
│   └── seed/
│       └── seed_data.sql          # small test seed (~50 rows/table)
│
├── dbt/                           # dbt project skeleton (Bloc 2: structure only)
│   └── noureddine/
│       ├── dbt_project.yml
│       ├── profiles.yml.example
│       ├── models/
│       │   ├── bronze/.gitkeep
│       │   ├── silver/.gitkeep
│       │   └── gold/.gitkeep
│       └── README.md              # "Models implemented in Bloc 3"
│
├── dags/                          # Airflow DAGs (Bloc 2: empty skeleton)
│   ├── .gitkeep
│   └── README.md                  # "DAGs implemented in Bloc 3"
│
├── api/                           # FastAPI serving (Bloc 4 placeholder)
│   └── README.md                  # "API implemented in Bloc 4"
│
├── ml/                            # ML training / models (Bloc 4 placeholder)
│   └── README.md
│
├── monitoring/                    # Evidently & alerting (Bloc 4 placeholder)
│   └── README.md
│
└── .github/
    └── workflows/
        └── ci.yml                 # minimal: lint SQL / validate compose / sanity checks
```

**Naming conventions:**
- SQL files: numbered prefixes (`01_`, `02_`…) so execution order is explicit.
- Tables: `snake_case`, singular-domain plural-table (e.g. `customers`, `order_items`).
- Warehouse: dimensions `dim_*`, facts `fact_*`, surrogate keys `*_key`, natural keys `*_id`.
- Schemas in PostgreSQL: `oltp`, `bronze`, `silver`, `gold`.
- Branches: `main` protected; feature work on `bloc2/...` branches; PR into main.
- Commits: Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`, `infra:`).

---

## 6. Data Model (governs SQL)

### OLTP transactional tables (schema `oltp`)
- `customers` (customer_id UUID PK, email, first_name, last_name, country, city, consent_marketing BOOL, created_at, updated_at)
- `categories` (category_id UUID PK, category_name, created_at) — e.g. Qamis, Grooming, Accessory, GiftSet
- `products` (product_id UUID PK, sku UNIQUE, product_name, category_id FK, price_eur, cost_eur, seasonality_tag, created_at, updated_at)
- `inventory` (inventory_id UUID PK, product_id FK, stock_quantity, reorder_threshold, last_updated)
- `orders` (order_id UUID PK, customer_id FK, order_date, total_amount, discount_amount, shipping_cost, payment_status, order_status, acquisition_channel, created_at)
- `order_items` (order_item_id UUID PK, order_id FK, product_id FK, quantity, unit_price, line_total)
- `shipments` (shipment_id UUID PK, order_id FK, carrier, tracking_number, shipping_date, delivery_date, shipment_status)
- `marketing_events` (event_id UUID PK, customer_id FK, source, campaign_name, event_type, event_timestamp)
- `rag_conversations` (conversation_id UUID PK, customer_id FK, question, intent, conversation_timestamp)
- `calendar_events` (calendar_event_id UUID PK, event_name, event_type, start_date, end_date) — e.g. Ramadan, Aid Al Fitr, Aid Al Adha, Nikah Season, Black Friday, Summer Sale

### Analytical star schema (schema `gold`)
- `dim_customer` (customer_key PK, customer_id, country, city, segment, acquisition_source)
- `dim_product` (product_key PK, product_id, sku, product_name, category, seasonality_tag)
- `dim_date` (date_key PK, date, day, week, month, quarter, year, is_weekend)
- `dim_channel` (channel_key PK, channel_name)
- `dim_calendar_event` (calendar_event_key PK, event_name, event_type)
- `fact_sales` (sale_key PK, order_id, customer_key FK, product_key FK, date_key FK, channel_key FK, calendar_event_key FK, quantity, revenue, discount, shipping_cost, margin)

### Relationships
customers → orders → order_items → products; products → inventory; orders → shipments; customers → marketing_events; customers → rag_conversations; calendar_events referenced by fact_sales via dim_calendar_event.

### Mandatory indexes
`customers.email`, `products.sku`, `orders.order_date`, `order_items.product_id`, `orders.customer_id`, `fact_sales.calendar_event_key` (and other FK columns).

### Governance mapping (from Bloc 1)
- `customers`, `orders`, `rag_conversations` → **C3 Confidential** (PII). 
- payment-related fields → **C4 Restricted**.
- product/inventory/calendar → **C2 Internal**.
- Seed data must be obviously fake (no real personal data).

---

## 7. Working Conventions for Claude Code

- **Idempotency:** all DDL uses `CREATE SCHEMA IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, `DROP ... IF EXISTS` guards where helpful, so re-runs don't break.
- **Auto-init:** PostgreSQL container must run the DDL + seed automatically on first boot (via mounted init folder).
- **Health-checks:** every service in `docker-compose.yml` has a `healthcheck`. `healthcheck.sh` verifies all are healthy and that expected tables/rows exist.
- **No secrets in git:** real secrets only in `.env` (git-ignored). `.env.example` documents every variable.
- **Verify before push:** bring the stack up, run the health-check, confirm pgAdmin connects and tables exist, THEN commit & push.
- **Docs as you go:** every architecture decision → a short ADR in `docs/bloc2-architecture/adr/`. Every diagram → Mermaid source committed.
- **Don't over-build:** Bloc 2 = architecture + schema + infra + docs. No pipeline logic, no ML, no API code beyond placeholders.
- **Ask nothing, assume this file:** if a detail is unspecified, choose the simplest option consistent with this file and record it in an ADR.

---

## 8. Definition of Done (per Bloc)

A Bloc is done when:
1. The code matches the scope defined here (no more, no less).
2. `docker compose up` (or `infra/scripts/up.sh`) brings the whole stack up cleanly.
3. `infra/scripts/healthcheck.sh` passes (all services healthy, tables present, seed loaded).
4. Documentation (README + Bloc docs + diagrams + ADRs) is complete and accurate.
5. Everything is committed and pushed to GitHub on a clean history.
6. A short "How to demo" section exists in the Bloc doc for the screencast video.
