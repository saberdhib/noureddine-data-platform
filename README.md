# NOUREDDINE Data Platform

> End-to-end data platform for a premium D2C menswear e-commerce brand.
> Built as a PFE (end-of-study project) — RNCP certification, Data Engineering / Data Architecture track.

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Customer & Data Journey](#2-customer--data-journey)
3. [Technology Stack](#3-technology-stack)
4. [Architecture at a Glance](#4-architecture-at-a-glance)
5. [Prerequisites](#5-prerequisites)
6. [How to Run](#6-how-to-run)
7. [How to Verify](#7-how-to-verify)
8. [Service URLs & Default Credentials](#8-service-urls--default-credentials)
9. [How to Tear Down](#9-how-to-tear-down)
10. [Repository Structure](#10-repository-structure)
11. [How to Demo (Screencast)](#11-how-to-demo-screencast)
12. [Bloc Roadmap](#12-bloc-roadmap)

---

## 1. Project Overview

**NOUREDDINE** is a premium direct-to-consumer menswear brand serving the Western Muslim diaspora. The data platform solves the core business problem: piloting **limited stock against irregular, event-driven demand** driven by the Islamic cultural calendar (Ramadan, Eid al-Fitr, Eid al-Adha, Nikah season) and retail peaks (Black Friday, Summer Sale).

The platform is built across 4 Blocs:

| Bloc | Theme | Status |
|------|-------|--------|
| Bloc 1 | Data Governance (policy, RGPD, RACI, risks) | ✅ Done |
| Bloc 2 | Data Architecture (infra, warehouse schema, Docker) | ✅ **Current** |
| Bloc 3 | Data Pipelines (Airflow DAGs, dbt, data quality) | ⏳ Next |
| Bloc 4 | AI / MLOps (forecasting model, FastAPI, Evidently) | ⏳ After |

---

## 2. Customer & Data Journey

```
User arrives (Instagram / TikTok / affiliate / paid ad / QR / web search)
    ↓
Shopify-powered website (products, stock, cart, delivery, tracking)
    ↓
RAG shopping assistant (style advice, questionnaire, photo upload, virtual try-on)
    ↓
Purchase → Back-office scan → Special customer code → Shipping label
    ↓
Customer registry → Confirmation + tracking emails
    ↓
Post-sale: personalised advice, new arrivals, loyalty programme
    ↓
Analytics: RAG queries, product interest, channel attribution, demand forecast
    ↓
Operations: stock management, forecast alerts, fraud detection, SAV
```

---

## 3. Technology Stack

| Layer | Tool | Version | Notes |
|-------|------|---------|-------|
| Object storage (Data Lake) | **MinIO** | latest stable | S3-compatible; maps 1:1 to AWS S3 |
| Warehouse / OLTP + OLAP | **PostgreSQL** | 16 | OLTP tables + analytical star schema |
| Orchestration | **Apache Airflow** | 2.9.1 | Skeleton in Bloc 2; DAGs in Bloc 3 |
| Transformation | **dbt** (dbt-postgres) | — | Skeleton in Bloc 2; models in Bloc 3 |
| DB admin | **pgAdmin** | 4 (v8) | Pre-registered server connection |
| Serving (API) | **FastAPI** | — | Placeholder; implemented in Bloc 4 |
| ML monitoring | **Evidently** | — | Placeholder; implemented in Bloc 4 |
| Containerisation | **Docker Compose** | v3.9 | Single-command local stack |
| Versioning | **Git + GitHub** | — | Mono-repo |

**Zero-licence, zero-cost:** all tools are free/open-source and run on a standard laptop.

---

## 4. Architecture at a Glance

```
Sources              Ingestion          Storage / DWH              Consumption
─────────────────    ─────────────────  ─────────────────────────  ───────────
Shopify API     ──►  Airflow DAGs  ──►  MinIO (Bronze)   ──►       pgAdmin
Marketing APIs  ──►  (Bloc 3)           MinIO (Silver)             (BI / SQL)
RAG logs        ──►                     MinIO (Gold)      ──►       FastAPI
Manual CSVs     ──►                     PostgreSQL        ──►       (Bloc 4)
                                        ├── oltp schema             Evidently
                                        ├── bronze schema           (Bloc 4)
                                        ├── silver schema
                                        └── gold schema
                                            (star schema)
```

---

## 5. Prerequisites

- **Docker Desktop** ≥ 24 with Docker Compose v2
- **Git**
- 4 GB RAM available for Docker (8 GB recommended)
- Ports `5432`, `5050`, `8080`, `9000`, `9001` free

Optional:
- `gh` CLI (for GitHub operations)
- `psql` CLI (for direct DB inspection)

---

## 6. How to Run

```bash
# 1. Clone the repository
git clone https://github.com/<your-org>/noureddine-data-platform.git
cd noureddine-data-platform

# 2. (Optional) Edit .env with custom secrets
cp .env.example .env
# nano .env  # change passwords if deploying anywhere non-local

# 3. Bring the stack up
bash infra/scripts/up.sh
# Equivalent: docker compose -f infra/docker-compose.yml up -d
```

On **first boot**, PostgreSQL automatically:
1. Creates schemas: `oltp`, `bronze`, `silver`, `gold`
2. Creates all OLTP tables (10 tables) and the analytical star schema (5 dims + `fact_sales`)
3. Creates all indexes and views
4. Loads the synthetic seed dataset (~50 rows per main table)

MinIO automatically creates buckets: `bronze`, `silver`, `gold`.

Wait ~60 seconds for Airflow to initialise its metadata database.

---

## 7. How to Verify

```bash
bash infra/scripts/healthcheck.sh
```

Expected output: all ✅ (services healthy, tables present, seed rows counted, buckets present).

You can also verify manually:
```bash
# PostgreSQL via psql
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "\dt oltp.*"
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "SELECT COUNT(*) FROM oltp.customers;"
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "SELECT COUNT(*) FROM gold.fact_sales;"

# Check views
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "SELECT * FROM gold.v_daily_revenue LIMIT 5;"
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "SELECT * FROM gold.v_sales_by_calendar_event;"
```

---

## 8. Service URLs & Default Credentials

| Service   | URL                     | Default credentials (from `.env.example`) |
|-----------|-------------------------|-------------------------------------------|
| pgAdmin   | http://localhost:5050   | `admin@noureddine.com` / `change_me_pgadmin` |
| MinIO UI  | http://localhost:9001   | `minio_admin` / `change_me_minio` |
| Airflow   | http://localhost:8080   | `admin` / `change_me_airflow` |
| PostgreSQL| `localhost:5432`        | `noureddine_user` / `change_me_postgres` (DB: `noureddine`) |

> **Security note:** Change all default passwords before exposing any service outside localhost.

---

## 9. How to Tear Down

```bash
# Stop containers, keep data volumes
bash infra/scripts/down.sh

# Full reset — stops containers AND deletes all data
bash infra/scripts/down.sh --volumes
```

---

## 10. Repository Structure

```
noureddine-data-platform/
├── README.md                      ← You are here
├── CLAUDE.md                      ← Permanent project context for Claude Code
├── .gitignore
├── .env.example                   ← All env vars (no secrets)
├── LICENSE                        ← MIT
│
├── docs/
│   ├── bloc1-governance/          ← Bloc 1 deliverables (Word/PPTX)
│   ├── bloc2-architecture/        ← Architecture docs, ADRs, diagrams
│   ├── bloc3-pipelines/           ← Placeholder
│   └── bloc4-mlops/               ← Placeholder
│
├── infra/
│   ├── docker-compose.yml         ← Full local stack
│   ├── postgres/init/             ← Auto-executed SQL on first boot
│   ├── pgadmin/servers.json       ← Pre-registered DB connection
│   ├── minio/                     ← Bucket notes
│   ├── airflow/                   ← Airflow skeleton notes
│   └── scripts/                   ← up.sh, down.sh, healthcheck.sh
│
├── sql/
│   ├── ddl/                       ← Schema + table + index + view definitions
│   └── seed/                      ← Synthetic test data
│
├── dbt/noureddine/                ← dbt project skeleton
├── dags/                          ← Airflow DAGs placeholder
├── api/                           ← FastAPI placeholder (Bloc 4)
├── ml/                            ← ML training placeholder (Bloc 4)
├── monitoring/                    ← Evidently placeholder (Bloc 4)
└── .github/workflows/ci.yml       ← Minimal CI
```

---

## 11. How to Demo (Screencast)

For the Bloc 2 demo video (3–5 min):

1. **Start the stack** — run `bash infra/scripts/up.sh` in terminal, show logs streaming up.
2. **Health check** — run `bash infra/scripts/healthcheck.sh`, show all ✅ printed.
3. **pgAdmin** — open `http://localhost:5050`, log in, expand the NOUREDDINE server:
   - Show `oltp` schema: browse `customers`, `orders`, `products`, `inventory` tables with row counts.
   - Show `gold` schema: browse `fact_sales`, `dim_customer`, `dim_product`, `dim_date`.
   - Run a query on `gold.v_sales_by_calendar_event` to show Ramadan / Eid revenue.
4. **MinIO console** — open `http://localhost:9001`, log in, show `bronze`, `silver`, `gold` buckets.
5. **Airflow** — open `http://localhost:8080`, log in, show the scheduler running (no DAGs yet — explain Bloc 3).
6. **Architecture diagram** — open `docs/bloc2-architecture/diagrams/logical-architecture.mmd` (rendered), narrate the data flow from sources through medallion layers to consumption.

---

## 12. Bloc Roadmap

| Bloc | Deliverable | Stack additions |
|------|-------------|-----------------|
| Bloc 3 | Airflow DAGs + dbt models + Great Expectations | DAG files, dbt models |
| Bloc 4 | Sales forecasting model + FastAPI + CI/CD + Evidently | `/api`, `/ml`, GitHub Actions full pipeline |
