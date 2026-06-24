# NOUREDDINE Data Platform — Architecture Summary (as-built)

> **Factual state of the repository's infrastructure.** Every item below is sourced from real files
> in this repo (paths in `backticks`). Nothing is proposed or recommended — this is an inventory.
> Where something does not exist, it is marked **not present**.
> Source of truth parsed: `infra/docker-compose.yml`, `infra/postgres/init/*.sql`, `infra/**`,
> `.env.example`, `.gitignore`, `docs/bloc2-architecture/`.

---

## 1. Deployed stack (current on-premise / Docker Compose)

Defined in `infra/docker-compose.yml`. Nine services, one bridge network, five named volumes.

| Service | Image (exact) | Build context | Host→container ports | Healthcheck | depends_on (condition) |
|---------|---------------|---------------|----------------------|-------------|------------------------|
| `postgres` | `postgres:16` | — | `${POSTGRES_PORT:-5432}:5432` | `pg_isready` (10s/5) | — |
| `minio` | `minio/minio:latest` | — | `${MINIO_API_PORT:-9000}:9000`, `${MINIO_CONSOLE_PORT:-9001}:9001` | `mc ready local` (15s/5) | — |
| `minio-init` | `minio/mc:latest` | — | none | **not present** | `minio` (service_healthy) |
| `pgadmin` | `dpage/pgadmin4:8` | — | `${PGADMIN_PORT:-5050}:80` | `wget /misc/ping` (15s/5) | `postgres` (service_healthy) |
| `airflow` | `noureddine-airflow:local` | `./airflow` (`FROM apache/airflow:2.9.1`) | `${AIRFLOW_PORT:-8080}:8080` | `curl /health` (30s/10) | `postgres` (service_healthy) |
| `simulator` | `noureddine/simulator:bloc3` | `..` (`simulator/Dockerfile`, `FROM python:3.11-slim`) | none | **not present** | `postgres` + `minio` (service_healthy) |
| `api` | `noureddine/api:bloc4` | `..` (`api/Dockerfile`, `FROM python:3.11-slim`) | `${API_PORT:-8000}:8000` | `curl /health` (30s/5) | `postgres` (service_healthy) |
| `streamlit` | `noureddine/streamlit:bloc4` | `..` (`streamlit/Dockerfile`, `FROM python:3.11-slim`) | `${STREAMLIT_PORT:-8501}:8501` | `curl /_stcore/health` (30s/5) | `api` (service_healthy) |
| `grafana` | `grafana/grafana:11.1.0` | — | `${GRAFANA_PORT:-3000}:3000` | `wget /api/health` (30s/5) | `postgres` (service_healthy) |

### Role of each service & medallion layer

| Service | Role | Medallion / layer |
|---------|------|-------------------|
| `postgres` | OLTP transactional DB **and** analytical warehouse (single engine, ADR-0003); also hosts the `airflow` metadata DB | **OLTP** + **Silver** + **Gold** (Postgres schemas) |
| `minio` | S3-compatible object storage (data lake) | **Bronze** (raw), plus `silver`/`gold` buckets |
| `minio-init` | One-shot job: creates buckets `bronze`, `silver`, `gold` | Bronze/Silver/Gold (lake provisioning) |
| `pgadmin` | Web DB admin / SQL browser (pre-registered server) | Cross-cutting (admin/observability) |
| `airflow` | Orchestration; runs `dags/ingest_orders.py` (Bloc 3) + `retrain_model`/`monitor_model` (Bloc 4). Image bakes dbt (isolated venv `/opt/dbt-venv`) + ML libs (`infra/airflow/requirements-airflow.txt`) | Ingestion / transformation (OLTP→Silver→Gold) |
| `simulator` | Generates synthetic OLTP data + Bronze JSON (stateful catch-up) | Source → OLTP + Bronze |
| `api` | FastAPI model serving (`/predict`, X-API-Key) | Gold consumption (Bloc 4) |
| `streamlit` | Business app (4 pages) consuming the API + Gold | Gold consumption (Bloc 4) |
| `grafana` | Dashboards over Postgres `monitoring` schema | Observability (Bloc 3/4) |

### Key environment variables per service (keys only; values from `.env` / defaults)

- `postgres`: `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`.
- `minio` / `minio-init`: `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`.
- `pgadmin`: `PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`, `PGADMIN_CONFIG_SERVER_MODE`, `PGADMIN_CONFIG_MASTER_PASSWORD_REQUIRED`.
- `airflow` (via `x-airflow-env` anchor): `AIRFLOW__CORE__EXECUTOR=LocalExecutor`, `AIRFLOW__CORE__LOAD_EXAMPLES=false`, `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`, `AIRFLOW__CORE__FERNET_KEY`, `AIRFLOW__WEBSERVER__SECRET_KEY`, `AIRFLOW__WEBSERVER__EXPOSE_CONFIG`, `AIRFLOW_ADMIN_*`, `POSTGRES_HOST/PORT/DB/USER/PASSWORD`, `DRIFT_THRESHOLD`, `MAPE_THRESHOLD`, `DBT_BIN`, `DBT_PROJECT_DIR`, `DBT_PROFILES_DIR`.
- `simulator`: `DATABASE_URL`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY_ID`, `MINIO_SECRET_ACCESS_KEY`, `BRONZE_BUCKET`, `CATCH_UP_INTERVAL_SECONDS`.
- `api`: `POSTGRES_*`, `API_KEY`.
- `streamlit`: `POSTGRES_*`, `API_URL`, `API_KEY`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `RESTOCK_LEAD_TIME_DAYS`.
- `grafana`: `GF_SECURITY_ADMIN_USER`, `GF_SECURITY_ADMIN_PASSWORD`, `GF_USERS_ALLOW_SIGN_UP`, `NOUREDDINE_DB_HOST/NAME/USER/PASSWORD`.

---

## 2. Data model

DDL auto-executed on first Postgres boot from `infra/postgres/init/` (alphanumeric order).

| File | Purpose |
|------|---------|
| `00_create_airflow_db.sql` | Creates the `airflow` metadata database (idempotent `\gexec`) |
| `01_create_schemas.sql` | Creates schemas `oltp`, `bronze`, `silver`, `gold` |
| `02_create_tables_oltp.sql` | 10 OLTP tables |
| `03_create_tables_warehouse.sql` | Gold star schema (5 dims + 1 fact) |
| `04_create_indexes.sql` | Indexes (present) |
| `05_create_views.sql` | 3 Gold analytical views |
| `06_seed_data.sql` | Synthetic seed (~50 rows/table) |
| `07_create_monitoring.sql` | `monitoring` schema (3 tables) |

### Schemas and table counts (from the init DDL)

| Schema | # tables in init DDL | Tables |
|--------|----------------------|--------|
| `oltp` | **10** | `customers`, `categories`, `products`, `inventory`, `orders`, `order_items`, `shipments`, `marketing_events`, `rag_conversations`, `calendar_events` |
| `gold` | **6** (+3 views) | `dim_customer`, `dim_product`, `dim_date`, `dim_channel`, `dim_calendar_event`, `fact_sales`; views `v_daily_revenue`, `v_sales_by_calendar_event`, `v_top_products` |
| `monitoring` | **3** | `pipeline_runs`, `model_metrics`, `retrain_events` |
| `bronze` | **0** | Empty in DDL — raw data lives as files in the MinIO `bronze` bucket |
| `silver` | **0** | Empty in DDL — populated at runtime by dbt as views (Bloc 3) |
| `simulator` | n/a | **not present in init** — schema `simulator` (`simulator.state`) is created at runtime by `simulator/state.py` |

### Star schema (gold)

- **Fact table:** `gold.fact_sales` (grain = order line). PK `sale_key BIGINT GENERATED ALWAYS AS IDENTITY`.
- **Dimensions:** `gold.dim_customer`, `gold.dim_product`, `gold.dim_date`, `gold.dim_channel`, `gold.dim_calendar_event` — each PK `*_key BIGINT GENERATED ALWAYS AS IDENTITY`.

### Primary / foreign keys (principal)

OLTP (`02_create_tables_oltp.sql`) — UUID PKs (`gen_random_uuid()`):

| Table | PK | FKs |
|-------|----|-----|
| `oltp.categories` | `category_id` | — |
| `oltp.calendar_events` | `calendar_event_id` | — |
| `oltp.customers` | `customer_id` | — |
| `oltp.products` | `product_id` | `category_id → oltp.categories` |
| `oltp.inventory` | `inventory_id` | `product_id → oltp.products` (UNIQUE) |
| `oltp.orders` | `order_id` | `customer_id → oltp.customers` |
| `oltp.order_items` | `order_item_id` | `order_id → oltp.orders`, `product_id → oltp.products` |
| `oltp.shipments` | `shipment_id` | `order_id → oltp.orders` |
| `oltp.marketing_events` | `event_id` | `customer_id → oltp.customers` (nullable) |
| `oltp.rag_conversations` | `conversation_id` | `customer_id → oltp.customers` (nullable) |

Gold (`03_create_tables_warehouse.sql`) — `fact_sales` foreign keys:

| Column | References |
|--------|-----------|
| `customer_key` | `gold.dim_customer(customer_key)` (NOT NULL) |
| `product_key` | `gold.dim_product(product_key)` (NOT NULL) |
| `date_key` | `gold.dim_date(date_key)` (NOT NULL) |
| `channel_key` | `gold.dim_channel(channel_key)` (NOT NULL) |
| `calendar_event_key` | `gold.dim_calendar_event(calendar_event_key)` (nullable) |

> Note: at OLTP level there is **no direct `orders → calendar_events` FK**; the order↔event link
> exists only at Gold level via `fact_sales.calendar_event_key` (assigned by dbt at build time).

### ERD location

- ERD: `docs/bloc2-architecture/diagrams/erd.mmd`
- Star schema: `docs/bloc2-architecture/diagrams/star-schema.mmd`
- Narrative model: `docs/bloc2-architecture/data-model.md`

---

## 3. Network & volumes

- **Network:** one user-defined bridge network `noureddine_net` (`driver: bridge`). All services join it.
- **Named volumes (persistence):** `postgres_data` (`/var/lib/postgresql/data`), `minio_data` (`/data`), `pgadmin_data` (`/var/lib/pgadmin`), `airflow_logs` (`/opt/airflow/logs`), `grafana_data` (`/var/lib/grafana`).
- **Bind mounts (read-only config / code):** `./postgres/init`, `./pgadmin/servers.json`, `./grafana/provisioning`, `./grafana/dashboards`, `../dags` (ro), `../ml/models` (ro for `api`); read-write: `../dbt`, `../ml`, `../monitoring` (for `airflow`).
- **Persistence strategy:** stateful data (DB, object store, dashboards, Airflow logs) lives in named volumes that survive `down.sh`; `down.sh --volumes` / `docker compose down -v` deletes them for a full reset.

---

## 4. Monitoring / observability

**Exists now:**
- **Docker healthchecks** on `postgres`, `minio`, `pgadmin`, `airflow`, `api`, `streamlit`, `grafana` (none on `minio-init`, `simulator`).
- **`infra/scripts/healthcheck.sh`** — verifies container health, schemas/tables/rows, MinIO buckets, and the Bloc 4 endpoints (API/Streamlit/Grafana, `current.pkl`).
- **pgAdmin** (`dpage/pgadmin4:8`) at `:5050`, server pre-registered via `infra/pgadmin/servers.json`.
- **Grafana** (`grafana/grafana:11.1.0`) at `:3000`, provisioned from `infra/grafana/`:
  - Datasource: `infra/grafana/provisioning/datasources/postgres.yml` (uid `noureddine_pg`).
  - Dashboards provider: `infra/grafana/provisioning/dashboards/dashboards.yml` → loads `infra/grafana/dashboards/noureddine_pipeline.json` (Bloc 3) and `model_health.json` (Bloc 4).
  - Backing data: Postgres `monitoring` schema (`pipeline_runs`, `model_metrics`, `retrain_events`).
- **Logs:** Airflow logs persisted in the `airflow_logs` volume; other services log to stdout (Docker logs).

**Planned / runtime-only (not in Bloc 2 infra):**
- Grafana panels are populated only after Bloc 3/4 DAGs run (DDL seeds one `pipeline_runs` row).
- Evidently HTML reports + `monitoring.model_metrics` rows are produced at runtime by `monitoring/evidently/generate_report.py` (Bloc 4), **not** by the Bloc 2 infra.
- Centralised log aggregation / alerting stack (ELK, Prometheus, etc.): **not present**.

---

## 5. Security

- **Secrets management:** all secrets via env vars; `.env` is git-ignored (`.gitignore`: `.env`, `*.env`, with `!.env.example`). `.env.example` documents every variable with placeholder values (no real secrets committed). Model binaries also ignored (`ml/models/*.pkl`, `ml/models/current.pkl`).
- **PostgreSQL roles:** a dedicated `00_create_roles.sql` is **not present**. Postgres runs with the single role from `POSTGRES_USER` (default `noureddine_user`), created by the `postgres:16` image entrypoint as the database owner/superuser. No granular least-privilege roles are defined in the repo.
- **Authentication in place:**
  - pgAdmin: login `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD`; `SERVER_MODE=False`, `MASTER_PASSWORD_REQUIRED=False`.
  - MinIO: root credentials `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD`.
  - Airflow: admin user created at boot (`AIRFLOW_ADMIN_*`); `FERNET_KEY` and `WEBSERVER__SECRET_KEY` are **hard-coded literals** in `x-airflow-env` (`infra/docker-compose.yml`).
  - Grafana: `GF_SECURITY_ADMIN_USER/PASSWORD`, `GF_USERS_ALLOW_SIGN_UP=false`.
  - FastAPI: `X-API-Key` header checked against `API_KEY` env (`api/auth.py`) on `/predict`, `/retrain`.
- **Network exposure:** all services publish to `localhost` ports; no TLS / reverse proxy is configured (**not present**).

---

## 6. IaC & reproducibility

- **No Terraform / Kubernetes** (ADR-0002). IaC = Docker Compose only (`infra/docker-compose.yml`). A top-level `/terraform`, `/docker`, `/k8s` directory is **not present** (mapping documented in `docs/bloc2-architecture/README.md`).
- **Lifecycle scripts** (`infra/scripts/`):
  - `up.sh` → `docker compose -f infra/docker-compose.yml --env-file .env up -d --remove-orphans`
  - `down.sh` → `docker compose ... down` (or `down -v` with `--volumes`)
  - `healthcheck.sh` → end-to-end verification
- **First-boot automation:** Postgres init DDL + seed run automatically (mounted at `/docker-entrypoint-initdb.d`); MinIO buckets created by `minio-init`; simulator self-bootstraps.
- **READMEs present:** root `README.md`; `infra/airflow/README.md`, `infra/minio/README.md`, `infra/grafana/README.md`; `docs/bloc2-architecture/README.md`, `architecture.md`, `data-model.md`.
- **Bloc 2 ADRs** (`docs/bloc2-architecture/adr/`): `0001-minio-over-s3.md`, `0002-no-kubernetes-terraform.md`, `0003-postgres-single-engine-oltp-and-warehouse.md`, `0004-airflow-skeleton-executor-choice.md`, `0005-medallion-schemas-in-postgres.md`.
- **CI:** `.github/workflows/ci.yml` validates compose config, SQL DDL, dbt parse/compile, and Bloc 4 tests.

---

## 7. Cloud compatibility (evidence in code)

- **S3-compatible object storage:** `simulator/common.py` connects to MinIO with the AWS SDK (`boto3.client("s3", endpoint_url=MINIO_ENDPOINT, aws_access_key_id=…, aws_secret_access_key=…, config=Config(signature_version="s3v4"), region_name="us-east-1")`. `MINIO_ENDPOINT` defaults to `http://minio:9000`. → Swapping the endpoint/credentials for AWS S3 requires no code change. Documented in ADR-0001 and `infra/minio/README.md` (bronze/silver/gold bucket mapping).
- **PostgreSQL portability:** all DB access is via standard `postgresql+psycopg2://` connection strings / `POSTGRES_HOST/PORT/DB/USER/PASSWORD` env vars (e.g. `AIRFLOW__DATABASE__SQL_ALCHEMY_CONN`, `simulator` `DATABASE_URL`, Grafana `NOUREDDINE_DB_*`). → Pointing `POSTGRES_HOST` at an AWS RDS endpoint requires no code change. No Postgres-proprietary infra dependency.
- **Config via env vars** throughout (`.env.example`) → 12-factor style, portable to ECS/EKS task definitions.
- **Explicit managed-cloud manifests (Terraform/EKS/RDS/S3 IaC):** **not present** (out of scope per ADR-0002).

---

## 8. Infrastructure file tree

```
infra/
├── airflow/
│   ├── Dockerfile                 # FROM apache/airflow:2.9.1 (+ dbt venv + ML libs)
│   ├── README.md
│   └── requirements-airflow.txt
├── docker-compose.yml             # 9 services, 1 network, 5 volumes
├── grafana/
│   ├── README.md
│   ├── dashboards/
│   │   ├── model_health.json
│   │   └── noureddine_pipeline.json
│   └── provisioning/
│       ├── dashboards/dashboards.yml
│       └── datasources/postgres.yml
├── minio/
│   └── README.md
├── pgadmin/
│   └── servers.json
├── postgres/
│   └── init/
│       ├── 00_create_airflow_db.sql
│       ├── 01_create_schemas.sql
│       ├── 02_create_tables_oltp.sql
│       ├── 03_create_tables_warehouse.sql
│       ├── 04_create_indexes.sql
│       ├── 05_create_views.sql
│       ├── 06_seed_data.sql
│       └── 07_create_monitoring.sql
└── scripts/
    ├── down.sh
    ├── healthcheck.sh
    └── up.sh
```

Related (not under `infra/`) but part of the data definition:
```
sql/
├── ddl/   (01_create_schemas … 06_create_monitoring)
├── seed/  (seed_data.sql)
└── monitoring/ (04_model_metrics.sql)
docs/bloc2-architecture/
├── README.md · architecture.md · data-model.md
├── adr/ (0001–0005)
└── diagrams/ (erd.mmd, star-schema.mmd, logical-architecture.mmd, technical-architecture.mmd, business-process.mmd)
```
