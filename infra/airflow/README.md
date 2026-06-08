# Airflow — Skeleton (Bloc 2)

## Current state (Bloc 2)

Airflow runs as a **skeleton only**:
- The `apache/airflow:2.9.1` image is deployed with LocalExecutor.
- The `dags/` folder is mounted but contains no DAG logic — only a README stub.
- The Airflow metadata database is stored in the shared PostgreSQL instance (separate `airflow` DB, created automatically on first boot).
- The webserver and scheduler are both started via a single `bash -c` entrypoint (appropriate for a local skeleton).

**ADR-0004** records the executor choice.

## Bloc 3 will add

- `dags/ingest_shopify.py` — pulls Shopify orders/customers → Bronze bucket (MinIO)
- `dags/ingest_marketing.py` — pulls marketing events → Bronze
- `dags/dbt_run.py` — triggers dbt Bronze→Silver→Gold transformations
- `dags/data_quality.py` — runs Great Expectations checkpoints; sends Slack alert on failure

## Access

Airflow UI: `http://localhost:8080`
Default credentials: see `.env.example` (`AIRFLOW_ADMIN_USERNAME`, `AIRFLOW_ADMIN_PASSWORD`)
