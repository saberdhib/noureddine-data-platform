# Bloc 3 — Data Pipelines

## Consigne → Repo Structure Mapping

The official Bloc 3 consigne expects `/dags /sql /python /tests`. This repo uses a
platform-oriented layout — each folder is named after its function, not the consigne label:

| Consigne | Repo path | Justification |
|----------|-----------|---------------|
| `/dags` | `/dags` | Direct match — Airflow DAGs |
| `/sql` | `/sql` | Direct match — DDL & seed |
| `/python` | `/simulator` | Named by purpose (data simulator), not language |
| `/tests` | `/tests` | Direct match — pytest smoke tests |
| *(new)* | `/dbt/noureddine` | dbt transformation layer |
| *(new)* | `/infra/grafana` | Grafana monitoring provisioning |
| *(new)* | `/docs/bloc3-pipelines` | This documentation |

This layout is organised by platform layer (ingest, transform, serve, monitor) rather than
by file type, which is standard practice for production data platforms and defensible in Q&A.

## Pipeline Overview

```
Simulator → OLTP + Bronze → Airflow (10 min) → dbt build → Silver + Gold → Grafana
```

See [`pipeline-architecture.md`](pipeline-architecture.md) for full detail.

## How to Run

### 1. Start the stack

```bash
bash infra/scripts/up.sh
# Waits for all services to be healthy
bash infra/scripts/healthcheck.sh
```

### 2. Start the simulator (bootstrap ~3y, then live catch-up)

```bash
docker compose -f infra/docker-compose.yml up -d simulator
docker logs -f noureddine_simulator
# First run bootstraps ~3 years (NOW-3y → NOW); thereafter it catches up to NOW()
# every CATCH_UP_INTERVAL_SECONDS (default 600). One process, no SIM_MODE.
# Wipe + re-bootstrap:  docker compose run --rm simulator python -m simulator.run --reset --once
```

### 4. Trigger the DAG / wait for schedule

Open Airflow at http://localhost:8080 (admin / change_me_airflow):
- DAGs → `ingest_orders` → Trigger Run
- Or wait for the 10-minute schedule to fire

### 5. View results

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://localhost:3000 | admin / change_me_grafana |
| Airflow | http://localhost:8080 | admin / change_me_airflow |
| pgAdmin | http://localhost:5050 | admin@noureddine.com / change_me_pgadmin |

### 6. Generate Elementary report

```bash
# Inside the dbt environment (or locally with dbt-elementary installed)
cd dbt/noureddine
edr report --profiles-dir . --project-dir .
# Opens elementary_report.html in browser
```

### 7. Run smoke tests

```bash
DATABASE_URL=postgresql+psycopg2://noureddine_user:change_me_postgres@localhost:5432/noureddine \
  pytest tests/test_pipeline.py -v
```

---

## How to Demo (Screencast)

Recommended sequence for a 5–10 minute demo recording:

1. **Show stack is up**: `bash infra/scripts/healthcheck.sh` — all green.

2. **Show history seeded**: open pgAdmin → oltp.orders → count ≈ 20k rows.
   Show `oltp.calendar_events` contains Ramadan/Eid fixed windows.

3. **Show seasonality**: query orders by month — spike visible in March 2025 (Ramadan/Eid).

4. **Show live catch-up**: `SELECT * FROM simulator.state;` — `last_generated_at` advances each
   cycle. Stop the simulator, wait, restart → it catches up the gap (watermark jumps), no duplicates.

5. **Trigger Airflow DAG**: Airflow UI → `ingest_orders` → Trigger.
   Show all 3 tasks turning green: `check_new_data` → `dbt_build` → `write_run_metadata`.

6. **Show silver/gold populated**: pgAdmin → `silver.stg_orders` (has rows) → `gold.fact_sales` (has rows).
   dbt test results: all green.

7. **Show Grafana**: http://localhost:3000 → NOUREDDINE dashboard → row counts updating,
   pipeline run history showing the last run.

8. **Show Elementary report**: open `elementary_report.html` → test pass-rate = 100%,
   model freshness, anomaly overview.

9. **Force a failure** (for alerting demo):
   - Stop drip, set `FORCE_FAILURE=1` in Airflow → Variables (or env)
   - Re-trigger `ingest_orders` — `dbt_build` fails
   - Show `on_failure_callback` in Airflow task logs: `ALERT {"alert": "pipeline_failure", ...}`
   - Show `monitoring.pipeline_runs` still records the run (trigger_rule: all_done)

10. **Restore**: unset `FORCE_FAILURE`, re-trigger → all green again.

---

## ADRs

| ADR | Decision |
|-----|----------|
| [0006](adr/0006-microbatch-over-streaming.md) | Micro-batch over streaming (Airflow + dbt, not Kafka) |
| [0007](adr/0007-elementary-for-data-quality.md) | Elementary for dbt-native data quality reporting |
| [0008](adr/0008-grafana-monitoring.md) | Grafana (Postgres datasource only) + gold ownership handover |

## Diagrams

- [`diagrams/pipeline-flow.mmd`](diagrams/pipeline-flow.mmd) — end-to-end data flow (renders on GitHub)
- [`diagrams/dag-graph.mmd`](diagrams/dag-graph.mmd) — Airflow DAG task graph
