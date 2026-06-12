# NOUREDDINE Data Platform

> End-to-end data platform for a premium D2C menswear e-commerce brand.
> PFE (end-of-study project) — RNCP certification, Data Engineering / Data Architecture track.
> **The 4 Blocs are delivered.** One mono-repo, one `docker compose` stack, zero-licence.

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Where to look — navigation by Bloc](#2-where-to-look--navigation-by-bloc) ⭐
3. [Technology Stack](#3-technology-stack)
4. [Architecture at a Glance](#4-architecture-at-a-glance)
5. [Prerequisites](#5-prerequisites)
6. [How to Run](#6-how-to-run)
7. [How to Verify](#7-how-to-verify)
8. [Service URLs & Default Credentials](#8-service-urls--default-credentials)
9. [How to Demo](#9-how-to-demo)
10. [Repository Structure](#10-repository-structure)
11. [Tear Down](#11-tear-down)

---

## 1. Project Overview

**NOUREDDINE** is a premium direct-to-consumer menswear brand serving the Western Muslim diaspora.
The platform solves the core business problem: piloting **limited stock against irregular,
event-driven demand** driven by the Islamic cultural calendar (Ramadan, Eid al-Fitr, Eid al-Adha,
Nikah season) and retail peaks (Black Friday, Summer Sale).

| Bloc | Theme | Status |
|------|-------|--------|
| Bloc 1 | Data Governance (policy, RGPD, RACI, classifications C1–C4, DPIA) | ✅ Done |
| Bloc 2 | Data Architecture (Postgres warehouse, MinIO, Docker, ADRs) | ✅ Done |
| Bloc 3 | Data Pipelines (simulator → Airflow → dbt → Elementary → Grafana) | ✅ Done |
| Bloc 4 | AI / MLOps (LightGBM, FastAPI, Evidently, Streamlit + optional AI advisor) | ✅ Done |

> Two audit passes hardened the platform: **`AUDIT_REPORT.md`** (Blocs 2+3) and
> **`AUDIT_REPORT_BLOC4.md`** (Bloc 4) — each with a component-by-component status and a
> copy-paste **manual testing guide**.

---

## 2. Where to look — navigation by Bloc ⭐

> *"If it's about Bloc X, read these files."*

| Bloc | Read the docs | Code lives in | Audit / testing guide |
|------|---------------|---------------|------------------------|
| **1 — Governance** | `docs/bloc1-governance/` → `README.md`, `data-asset-catalogue-v2.md`, `annotation-rules.md` (+ Word/PPTX) | governance is enforced in `dbt/noureddine/models/**` `meta:` blocks | — |
| **2 — Architecture** | `docs/bloc2-architecture/` → `README.md`, `architecture.md`, `data-model.md`, `adr/` (0001–0005), `diagrams/` | `sql/ddl/`, `sql/seed/`, `infra/` | `AUDIT_REPORT.md` §C (1–3, 12, 15) |
| **3 — Pipelines** | `docs/bloc3-pipelines/` → `README.md`, `pipeline-architecture.md`, `adr/` (0006–0008), `diagrams/` | `simulator/`, `dags/ingest_orders.py`, `dbt/noureddine/`, `infra/grafana/` | `AUDIT_REPORT.md` §C (4–11, 13–14) |
| **4 — AI/MLOps** | `docs/bloc4-ai-mlops/` → `README.md` (**how-to-demo**), `architecture.md`, `model-card.md`, `cahier-des-charges.md`, `adrs/` (0009–0015), `diagrams/` | `ml/`, `api/`, `streamlit/`, `monitoring/evidently/`, `dags/retrain_model.py` + `monitor_model.py` | `AUDIT_REPORT_BLOC4.md` §C (1–16) |

Project source of truth: **`CLAUDE.md`** (business context, locked decisions, conventions).

---

## 3. Technology Stack

| Layer | Tool | Notes |
|-------|------|-------|
| Object storage (Data Lake) | **MinIO** | S3-compatible; maps 1:1 to AWS S3 (ADR-0001) |
| Warehouse / OLTP + OLAP | **PostgreSQL 16** | OLTP tables + analytical star schema |
| Data simulator | **Python** (`simulator/`) | One stateful **catch-up** process, Islamic-calendar seasonality |
| Orchestration | **Apache Airflow 2.9** | custom image `noureddine-airflow:local` (dbt + ML baked in) |
| Transformation | **dbt** (dbt-postgres 1.8.2) | 10 staging + 6 marts + 3 views, governance `meta`, data tests |
| Data quality | **Elementary** | dbt-test artifacts + HTML report |
| Forecasting model | **LightGBM** + **SHAP** | demand per category × day, 30-day horizon (ADR-0009) |
| Serving (API) | **FastAPI** | `/predict` etc., X-API-Key auth (ADR-0010) |
| ML monitoring | **Evidently** | drift + performance → `monitoring.model_metrics` (ADR-0011) |
| Dashboards | **Grafana** + **Streamlit** | Grafana = ops/Model Health; Streamlit = business app (ADR-0012) |
| Optional AI advisor | **OpenAI** | grounded restock briefing, opt-in via env key (ADR-0015) |
| DB admin | **pgAdmin 4** | pre-registered connection; shows governance comments |
| CI/CD | **GitHub Actions** | compose/SQL/dbt validation + ml/api/streamlit tests |
| Containerisation | **Docker Compose** | single-command local stack |

**Zero-licence, zero-cost** baseline — all core tools are free/open-source and run on a laptop. The
**AI advisor** (OpenAI) is the only optional, paid, opt-in extra (ADR-0015); the platform is fully
functional without it.

---

## 4. Architecture at a Glance

```
Simulator ─► oltp (Postgres) ─► [Airflow ingest_orders, every 10 min]
                                      │  dbt build
                                      ▼
                       silver (staging) ─► gold (star schema: dim_* + fact_sales + views)
                                                     │
       ┌─────────────────────────────────────────────┼───────────────────────────────┐
       ▼                         ▼                     ▼                               ▼
  Streamlit (business)     FastAPI /predict      Evidently + Grafana            retrain_model /
  4 pages + AI advisor  ◄── LightGBM model ──►   (Model Health)                 monitor_model DAGs
                                                                                 (drift-triggered)
Bronze/Silver/Gold buckets in MinIO mirror the lake layers.
```

---

## 5. Prerequisites

- **Docker Desktop** ≥ 24 with Compose v2 (daemon **running**)
- **Git**; ~8 GB RAM for Docker
- Free ports: `5432`, `5050`, `8080`, `9000`, `9001`, **`8000`, `8501`, `3000`**
- Optional: `psql`, `gh`, `jq`

---

## 6. How to Run

```bash
git clone https://github.com/saberdhib/noureddine-data-platform.git
cd noureddine-data-platform
cp .env.example .env            # (optional) set passwords + API_KEY; OPENAI_API_KEY only if you want the AI advisor

# 1. Build the images (the airflow image bakes in dbt + ML libs — Bloc 4 audit Fix A)
docker compose -f infra/docker-compose.yml build

# 2. Bring everything up
bash infra/scripts/up.sh        # == docker compose -f infra/docker-compose.yml up -d
```

On first boot Postgres auto-creates the schemas (`oltp/bronze/silver/gold/monitoring`), all tables,
indexes, views and the monitoring tables; MinIO creates the `bronze/silver/gold` buckets; the
**simulator** bootstraps ~3 years of history then catches up to now.

**Then populate gold and train the model:**
```bash
# Airflow http://localhost:8080 → trigger DAG `ingest_orders`  (oltp → dbt → silver/gold)
# Airflow → trigger DAG `retrain_model`                        (trains LightGBM, promotes current.pkl)
# (CLI equivalents: docker compose exec airflow /opt/dbt-venv/bin/dbt build … / python ml/src/train.py)
```

> **Punchy pre-Eid demo** (optional): `python ml/scripts/seed_demo_pre_eid.py` then `retrain_model`
> → tight inventory + an imminent Eid so the Streamlit **AI Advisor** flags urgent restocks.

---

## 7. How to Verify

```bash
bash infra/scripts/healthcheck.sh        # all ✅ (containers, schemas, data, buckets, API/Streamlit/Grafana)
docker compose -f infra/docker-compose.yml ps

# DB
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "\dn"
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "SELECT count(*) FROM gold.fact_sales;"

# API (set API_KEY from .env)
curl -s localhost:8000/health
curl -s -o /dev/null -w "%{http_code}\n" -X POST localhost:8000/predict -d '{"category":"Qamis","horizon":30}' -H 'Content-Type: application/json'  # 401
curl -s -X POST localhost:8000/predict -H "X-API-Key: $API_KEY" -H 'Content-Type: application/json' -d '{"category":"Qamis","horizon":30}' | jq '.forecast[:3]'
```
Full per-component testing guides: **`AUDIT_REPORT.md` §C** and **`AUDIT_REPORT_BLOC4.md` §C**.

---

## 8. Service URLs & Default Credentials

| Service | URL | Default credentials (`.env.example`) |
|---------|-----|--------------------------------------|
| pgAdmin | http://localhost:5050 | `admin@noureddine.com` / `change_me_pgadmin` |
| MinIO UI | http://localhost:9001 | `minio_admin` / `change_me_minio` |
| Airflow | http://localhost:8080 | `admin` / `change_me_airflow` |
| PostgreSQL | `localhost:5432` | `noureddine_user` / `change_me_postgres` (DB `noureddine`) |
| FastAPI | http://localhost:8000/docs | `X-API-Key: <API_KEY>` on `/predict`, `/retrain` |
| Streamlit | http://localhost:8501 | — (Executive · Demand Forecast · Stock Pilot · 🤖 AI Advisor) |
| Grafana | http://localhost:3000 | `admin` / `change_me_grafana` (Pipeline + Model Health) |

> Change all default passwords before exposing anything outside localhost. `.env` is gitignored —
> put `OPENAI_API_KEY` there to enable the AI advisor (leave empty to stay 100% zero-licence).

---

## 9. How to Demo

The detailed, copy-paste screencast scripts live in the docs:
- **Bloc 2/3 demo & testing** → `AUDIT_REPORT.md` §C + `docs/bloc3-pipelines/README.md`.
- **Bloc 4 demo (how-to-demo)** → `docs/bloc4-ai-mlops/README.md` + `AUDIT_REPORT_BLOC4.md` §C.

Short end-to-end tour: `up.sh` → `healthcheck.sh` green → pgAdmin (schemas + governance comments) →
MinIO buckets → Airflow trigger `ingest_orders` (dbt → silver/gold) → `retrain_model` → FastAPI
`/docs` + `curl /predict` → Streamlit 4 pages (calendar overlays on Demand Forecast, AI Advisor
restock briefing) → Grafana Model Health → `monitor_model` (+ `FORCE_DRIFT=1`) firing a retrain.

---

## 10. Repository Structure

```
noureddine-data-platform/
├── README.md                  ← you are here
├── CLAUDE.md                  ← project source of truth (context + locked decisions)
├── AUDIT_REPORT.md            ← Bloc 2/3 audit + testing guide
├── AUDIT_REPORT_BLOC4.md      ← Bloc 4 audit + testing guide
├── .env.example               ← all env vars (no secrets)
│
├── docs/
│   ├── bloc1-governance/      ← policy, catalogue v2, annotation rules
│   ├── bloc2-architecture/    ← architecture, data-model, ADRs 0001–0005, diagrams
│   ├── bloc3-pipelines/       ← pipeline-architecture, ADRs 0006–0008, diagrams
│   └── bloc4-ai-mlops/        ← how-to-demo, model-card, ADRs 0009–0015, diagrams
│
├── infra/
│   ├── docker-compose.yml     ← full stack (postgres, minio, pgadmin, airflow, simulator, api, streamlit, grafana)
│   ├── airflow/               ← custom airflow image (dbt + ML libs)
│   ├── postgres/init/         ← auto-run DDL + monitoring schema
│   ├── grafana/               ← datasource + Pipeline & Model-Health dashboards
│   └── scripts/               ← up.sh, down.sh, healthcheck.sh
│
├── sql/{ddl,seed,monitoring}/ ← schema, seed, monitoring DDL
├── simulator/                 ← stateful catch-up data simulator (run.py, state.py, seasonality.py)
├── dbt/noureddine/            ← staging + marts + tests + governance meta (Elementary)
├── dags/                      ← ingest_orders (Bloc 3) · retrain_model + monitor_model (Bloc 4)
├── ml/                        ← features/train/predict/retrain/model_card + tests + scripts
├── api/                       ← FastAPI serving (+ Dockerfile, tests)
├── streamlit/                 ← business app: 4 pages + lib (db, api_client, overlays, ai_advisor)
├── monitoring/evidently/      ← drift/performance report → monitoring.model_metrics
└── .github/workflows/ci.yml   ← validate + lint + dbt + ml/api/streamlit tests
```

---

## 11. Tear Down

```bash
bash infra/scripts/down.sh                 # stop containers, keep data
docker compose -f infra/docker-compose.yml down -v   # full reset (delete volumes)
```
