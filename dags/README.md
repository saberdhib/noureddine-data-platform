# Airflow DAGs — Bloc 3

## `ingest_orders` (micro-batch ingestion)

**File:** `ingest_orders.py`  
**Schedule:** `*/10 * * * *` (every 10 minutes)  
**Purpose:** Micro-batch pipeline — OLTP → dbt build (silver + gold) → run metadata

### Task graph

```
check_new_data → dbt_build → write_run_metadata
```

| Task | Type | Description |
|------|------|-------------|
| `check_new_data` | PythonOperator | Count orders created since last successful run |
| `dbt_build` | BashOperator | `dbt build --no-version-check` (run + test). Fails DAG if any dbt test fails. |
| `write_run_metadata` | PythonOperator | INSERT into `monitoring.pipeline_runs` (trigger_rule: all_done) |

### Alerting

`on_failure_callback` fires on any task failure:
- Logs a structured JSON payload: `ALERT {"alert": "pipeline_failure", "dag_id": ..., "task_id": ..., ...}`
- Optionally POSTs to `ALERT_WEBHOOK_URL` (env var, no paid service)

### Demo — forced failure

Set env var `FORCE_FAILURE=1` (Airflow Variables or container env) to make `dbt_build` fail
intentionally. The `on_failure_callback` fires and `write_run_metadata` still records the failed run.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NOUREDDINE_PG_CONN_ID` | `noureddine_postgres` | Airflow connection ID for PostgreSQL |
| `DBT_PROJECT_DIR` | `/opt/airflow/dbt/noureddine` | Path to dbt project inside the Airflow container |
| `DBT_PROFILES_DIR` | `/opt/airflow/dbt/noureddine` | Path to dbt profiles |
| `ALERT_WEBHOOK_URL` | *(unset)* | Optional webhook URL for failure alerts |
| `FORCE_FAILURE` | `0` | Set to `1` to force dbt_build failure (demo) |
