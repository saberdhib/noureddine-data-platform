# Architecture — NOUREDDINE Data Platform (Bloc 2)

## 1. Logical Architecture

The platform follows a **Medallion architecture** with three progressive data quality layers:

```
External Sources
  ├── Shopify (orders, products, inventory, customers)
  ├── Marketing platforms (Instagram, TikTok, affiliate)
  ├── RAG assistant logs (customer questions, intents)
  └── Manual event calendar (Ramadan, Eid, Nikah, Black Friday)
           │
           ▼
      [Ingestion — Airflow DAGs, Bloc 3]
           │
           ▼
   Bronze Layer (raw)
   ─────────────────
   MinIO bucket `bronze`
   PostgreSQL schema `bronze`
   → Unmodified copy of source data.
   → Append-only, never modified.
   → Governed as C2–C4 depending on table.
           │
           ▼
   Silver Layer (clean)
   ─────────────────────
   MinIO bucket `silver`
   PostgreSQL schema `silver`
   → Typed, deduplicated, quality-validated records.
   → dbt models apply schema validation, null checks, FK integrity.
   → PII masked / pseudonymised per Bloc 1 P-02 policy.
           │
           ▼
   Gold Layer (business-ready)
   ────────────────────────────
   MinIO bucket `gold`
   PostgreSQL schema `gold`  ← Star schema lives here
   → Analytical star schema: fact_sales + 5 dimensions.
   → ML-ready feature tables for Bloc 4 forecasting model.
   → Analytical views: v_daily_revenue, v_sales_by_calendar_event, v_top_products.
           │
           ▼
   Consumption
   ────────────
   → pgAdmin: ad-hoc SQL queries, data validation, ops dashboarding.
   → FastAPI (Bloc 4): prediction endpoint serving forecasting model.
   → Evidently (Bloc 4): ML monitoring, data drift detection.
```

## 2. Technical Architecture

All services run locally in Docker containers on a shared bridge network (`noureddine_net`).

### Services

| Container | Image | Role | Ports |
|-----------|-------|------|-------|
| `noureddine_postgres` | postgres:16 | OLTP + analytical warehouse | 5432 |
| `noureddine_minio` | minio/minio:RELEASE.2024-05-01 | S3-compatible Data Lake | 9000 (API), 9001 (console) |
| `noureddine_minio_init` | minio/mc | One-shot bucket creator | — |
| `noureddine_pgadmin` | dpage/pgadmin4:8 | Database admin UI | 5050 |
| `noureddine_airflow` | apache/airflow:2.9.1 | Orchestration (skeleton) | 8080 |

### Data flows (Bloc 2)

- **PostgreSQL auto-init:** on first boot, Postgres executes numbered SQL files in `infra/postgres/init/` — schemas, tables, indexes, views, then the seed.
- **MinIO auto-init:** `minio-init` (mc client) creates `bronze`, `silver`, `gold` buckets on first run.
- **Airflow:** connects to PostgreSQL for its metadata database (separate `airflow` DB). Mounts `dags/` read-only. No DAG logic until Bloc 3.

### Health checks

Every service declares a Docker `healthcheck`. `infra/scripts/healthcheck.sh` confirms:
1. All containers are in `healthy` state.
2. Key tables exist and contain seed rows.
3. MinIO buckets are accessible.

## 3. Design Justifications

### Governance tie-back (Bloc 1)

- Classification C3 (PII): `customers.email/first_name/last_name`, `rag_conversations.question` → restricted access, masked in Silver layer (Bloc 3).
- Classification C4 (Restricted): `orders.payment_status` → encrypted at rest in production.
- Quality dimensions (DAMA): completeness, accuracy, timeliness enforced by dbt tests in Silver layer (Bloc 3).
- Retention policy P-03: transactional data kept 5 years; marketing events 2 years.

### Free-tier / zero-licence constraint

All tools are open-source with no enterprise licences required:
- PostgreSQL (PostgreSQL Licence), MinIO (AGPL-3.0), Airflow (Apache 2.0), dbt-core (Apache 2.0), pgAdmin (PostgreSQL Licence).

### MinIO ↔ AWS S3 mapping

MinIO exposes the **full S3 API**. Migration to AWS S3 requires only:
1. Change the endpoint URL from `http://minio:9000` to the S3 bucket URL.
2. Replace `MINIO_ROOT_USER/PASSWORD` with IAM Access Key / Secret.
3. No application code changes.

### No Kubernetes / Terraform

At ~€8–9M revenue with a single-developer PFE scope, Kubernetes adds operational overhead disproportionate to the scale. Docker Compose provides the same reproducibility for local development. Documented in ADR-0002.

## 4. Security considerations

- All secrets in `.env` (git-ignored). `.env.example` documents variable names only.
- No hardcoded passwords in Docker Compose — all via environment variable substitution.
- Network isolation: services communicate on internal bridge `noureddine_net`; only required ports exposed to host.
- Seed data contains no real personal data (Bloc 1 governance C3 requirement).
