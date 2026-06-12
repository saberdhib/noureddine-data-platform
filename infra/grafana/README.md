# Grafana — Pipeline Monitoring

Grafana is provisioned automatically via `infra/grafana/provisioning/`.

## Access

| URL | `http://localhost:3000` |
|-----|------------------------|
| Username | `admin` (or `GRAFANA_ADMIN_USER` in `.env`) |
| Password | `change_me_grafana` (or `GRAFANA_ADMIN_PASSWORD` in `.env`) |

## Dashboards

**NOUREDDINE — Pipeline & Data Quality** (`noureddine-pipeline`):

| Panel | Query | What it proves |
|-------|-------|----------------|
| Silver orders row count | `COUNT(*) FROM silver.stg_orders` | Staging layer is being populated |
| Gold fact_sales count | `COUNT(*) FROM gold.fact_sales` | Gold star schema is live |
| Pipeline run history | `monitoring.pipeline_runs` | Airflow DAG is running on schedule |
| Last run status | `monitoring.pipeline_runs ORDER BY created_at DESC` | Pass/fail status of last DAG run |

## Datasource

PostgreSQL (Postgres 16, schema `noureddine`). Credentials from environment variables.

In a real AWS production deployment the equivalent would be **CloudWatch** (no cost to deploy,
native AWS integration). Grafana is used here to stay free and self-hosted (ADR 0008).

## No Prometheus

This stack uses Postgres as the single metrics store. No Prometheus/StatsD. All pipeline
metadata is written by the Airflow DAG into `monitoring.pipeline_runs` (a plain SQL table),
which Grafana queries directly. This is simpler and sufficient for an SME-scale platform.
