# Pipeline Architecture — Bloc 3

## Overview

Bloc 3 implements a **micro-batch data pipeline** (ADR 0006) that ingests synthetic e-commerce
data, transforms it through the medallion architecture, validates quality, and exposes monitoring
dashboards. The pipeline runs entirely in Docker Compose, zero external dependencies.

## Data Flow

```
Simulator → OLTP + Bronze → Airflow (every 10 min) → dbt build → Silver + Gold → Grafana
```

### 1. Data Simulator

**One process with stateful catch-up** — `python -m simulator.run` (no more `SIM_MODE`):

- **Bootstrap** (first run, empty `simulator.state`): upsert the fixed Islamic-calendar windows,
  create reference customers/products/inventory, and backfill ~3 years (`NOW-3y → NOW`) using the
  seasonality + growth + hour-of-day demand model.
- **Catch-up** (every run after, every `CATCH_UP_INTERVAL_SECONDS`): generate only the missing
  slice `(last_generated_at, NOW]`, then advance the watermark — so the warehouse is always current
  and a restart resumes exactly where it left off.

State is a singleton row in `simulator.state` (`last_generated_at`, `bootstrap_completed`); the
watermark is advanced in the same transaction as the writes. Order/line/shipment IDs are
**deterministic per hour bucket** (`uuid5` + `ON CONFLICT DO NOTHING`), so an overlapping window is
never duplicated. `--reset` truncates business tables + resets state, then re-bootstraps.

Writes to:
- **PostgreSQL `oltp` schema** — transactional records (customers, orders, order_items, shipments, etc.)
- **MinIO `bronze` bucket** — raw JSON, partitioned `orders/year=YYYY/month=MM/day=DD/batch.json`
  (best-effort, fail-fast so it never blocks OLTP generation).

### 2. Seasonality Model

All Islamic calendar dates are **fixed** (never computed). They are seeded into `oltp.calendar_events`.

Demand multipliers are **crossed with product category**:

| Event | Categories boosted | Multiplier |
|-------|-------------------|-----------|
| Pre-Eid al-Fitr (14 days) | Qamis, GiftSet | ×4.0 |
| Ramadan | Grooming, Qamis | ×2.5 |
| Eid al-Adha | Suit, ReadyToWear | ×2.8 |
| Nikah season (Jun–Aug) | Suit, Accessory, LeatherGoods | ×2.2 |
| Black Friday | all | ×3.2 |
| Baseline | all | ×1.0 |

Additional modifiers: ±15% random noise, +15%/year growth trend, weekend/payday uplift.

### 3. Airflow DAG: `ingest_orders`

Schedule: `*/10 * * * *` (every 10 minutes, demo-tunable).

```
check_new_data → dbt_build → write_run_metadata
```

- **`check_new_data`**: counts new OLTP orders since the last successful run (via XCom).
- **`dbt_build`**: runs `dbt build --no-version-check` (= `dbt run` + `dbt test`). Fails the DAG
  if any dbt test fails. `FORCE_FAILURE=1` env var triggers intentional failure for the demo.
- **`write_run_metadata`**: inserts a row into `monitoring.pipeline_runs` (trigger_rule: all_done,
  so it always records the outcome).
- **`on_failure_callback`**: logs a structured JSON alert to Airflow logs and (optionally) POSTs
  to `ALERT_WEBHOOK_URL` (env-configurable, no paid service required).

### 4. dbt Transformations

#### Staging (Bronze → Silver, schema `silver`)

One view per OLTP source table, cleaning types and conforming names:
`stg_customers`, `stg_orders`, `stg_order_items`, `stg_products`, `stg_categories`,
`stg_shipments`, `stg_calendar_events`, `stg_marketing_events`, `stg_rag_conversations`.

Generic tests: `not_null` on keys, `unique` on natural keys, `accepted_values` on status/category
fields, `relationships` on foreign keys.

#### Marts (Silver → Gold, schema `gold`)

Star schema with `+materialized: table` (dbt owns schema `gold` from Bloc 3 onward, ADR 0008):

- `dim_customer` — customer segments by consent/acquisition
- `dim_product` — product catalogue with category
- `dim_date` — date spine 2023–2027 with week/month/quarter/year/is_weekend
- `dim_channel` — distinct acquisition channels
- `dim_calendar_event` — Islamic calendar events for the `fact_sales` join
- `fact_sales` — grain: one row per order item, with quantity/revenue/discount/shipping/margin
  and FK keys to all dimensions

Singular tests:
- `assert_revenue_non_negative` — no negative revenue in `fact_sales`
- `assert_no_orphan_fact_sales` — no null `customer_key` in `fact_sales`

#### Elementary (ADR 0007)

`elementary.upload_dbt_artifacts()` runs after every `dbt build`, uploading test results and
run metadata into the `elementary` schema. The HTML quality report is generated with `edr report`.

### 5. Grafana Monitoring (ADR 0008)

Provisioned dashboards (PostgreSQL datasource only, no Prometheus):

| Panel | Source | Criterion |
|-------|--------|-----------|
| Silver order count | `silver.stg_orders` | Staging layer populated |
| Gold fact_sales count | `gold.fact_sales` | Gold star schema live |
| Pipeline run history | `monitoring.pipeline_runs` | DAG running on schedule |
| Last run status | `monitoring.pipeline_runs` | Pass/fail visibility |

In AWS production: **CloudWatch** would replace Grafana (native, managed). Not deployed here
to avoid cost (zero-licence constraint, ADR 0008).

## Quality Gates

1. **dbt generic tests** — run on every `dbt build` (every 10 min). Fail the DAG.
2. **dbt singular tests** — revenue ≥ 0, no orphan fact rows.
3. **Elementary** — anomaly detection over test result history. HTML report.
4. **Pipeline smoke tests** — `tests/test_pipeline.py` verifies silver/gold populated and
   seasonality is visible (Eid window ≥ 2x baseline order volume).

## Governance Ties (Bloc 1)

- **P-04 Data Quality** (DAMA dimensions: completeness, validity, consistency): enforced by
  dbt tests on every pipeline run; Elementary tracks trends over time.
- **C3 Confidential** (customer PII): simulator generates obviously fake identities (Faker,
  `@example.test` emails). No real personal data anywhere.
- **Bloc 2 gold DDL**: annotated as superseded; dbt is now the single source of truth for
  schema `gold` (ADR 0008). No two sources of truth (P-04 consistency).

## How to Run

```bash
# 1. Start the stack
bash infra/scripts/up.sh

# 2. Start the simulator (bootstraps ~3y on first run, then catches up to NOW
#    every CATCH_UP_INTERVAL_SECONDS). One process — no SIM_MODE.
docker compose -f infra/docker-compose.yml up -d simulator
docker logs -f noureddine_simulator        # watch bootstrap / catch-up

# 4. Trigger Airflow DAG or wait for schedule (every 10 min)
# Open http://localhost:8080 → DAGs → ingest_orders → Trigger

# 5. View monitoring
# Grafana:   http://localhost:3000  (admin / change_me_grafana)
# Airflow:   http://localhost:8080  (admin / change_me_airflow)
# pgAdmin:   http://localhost:5050

# 6. Generate Elementary report (inside dbt container or locally with dbt installed)
cd dbt/noureddine
edr report --profiles-dir . --project-dir .

# 7. Run smoke tests
DATABASE_URL=postgresql+psycopg2://noureddine_user:change_me_postgres@localhost:5432/noureddine \
  pytest tests/test_pipeline.py -v
```
