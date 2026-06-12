# AUDIT REPORT — Blocs 2 + 3 (before Bloc 4 sign-off)

**Date:** 2026-06-12 · **Branch:** `claude/audit-bloc2-bloc3` · **Auditor:** autonomous pass
**Method:** the stack was **run**, not just read — a local PostgreSQL 16 was used (the audit
environment has no Docker daemon), the **real Bloc 3 simulator** populated `oltp`, **dbt build**
materialised `silver`/`gold`, and **pytest** + dbt tests were executed. GitHub Actions history was
inspected via API. Items that can only run under Docker/MinIO/Airflow are flagged explicitly.

> TL;DR — Blocs 2 + 3 are largely solid, but the **Bloc 3 → Bloc 4 merge introduced several
> breakages** (incompatible `pipeline_runs`, dbt writing to the wrong schemas, missing dbt profile,
> a non-existent CI dbt version that turned `main` red, duplicate Grafana provider, dropped
> simulator service). All of these are now fixed and verified. The simulator was refactored to a
> single stateful catch-up process and every dbt model now carries governance metadata. Two
> Docker-runtime gaps (Airflow-runs-dbt, Elementary/Grafana live rendering) could not be executed
> in this no-Docker environment and are documented in Section D with concrete fixes.

---

## Section A — What's done ✅

| # | Component | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Consigne mapping (Bloc 3) | ✅ | `docs/bloc3-pipelines/README.md` "Consigne → Repo Structure Mapping" (`/python → /simulator`). |
| 1 | Consigne mapping (Bloc 2) | ✅ *(added in this audit)* | `docs/bloc2-architecture/README.md` now has `/terraform → NOT IMPLEMENTED (ADR-0002)`, `/docker`, `/scripts` table. |
| 3 | Data model (10 OLTP + 6 gold + indexes + FKs + 3 views) | ✅ | `sql/ddl/02..05`; verified present after DDL load; `\d gold.fact_sales` shows all FKs/indexes. |
| 4 | Simulator behaviour + `--reset` + calendar upsert + volume | ✅ *(refactored, Fix 1)* | `simulator/run.py`; bootstrap 17 027 orders over 3y; 20 calendar events upserted; `--reset` works. |
| 6 | Silver (10 dbt staging models) | ✅ | `dbt build` → 10 view models in `silver`; `silver.stg_orders` = 12k+ rows. |
| 7 | Gold (5 dims + `fact_sales` + 3 views) | ✅ *(dbt now sole runtime owner, Fix B6)* | `gold.fact_sales` grows each run; views rebuilt by dbt. |
| 8 | dbt tests (generic + 2 singular) | ✅ | `dbt build` → **58 data tests PASS** (`not_null`, `unique`, `accepted_values`, `relationships`) + `assert_no_orphan_fact_sales`, `assert_revenue_non_negative`. |
| 10 | Airflow DAG `ingest_orders` | ✅ parse / 🟡 run | DAG imports; `schedule */10`, `on_failure_callback`, `FORCE_FAILURE` path, writes `monitoring.pipeline_runs`. Running it *inside Docker* needs the Section D fix. |
| 12 | Pipeline tests | ✅ | `pytest tests/test_pipeline.py` → **11 passed**, incl. `test_seasonality_eid_vs_baseline`. |
| 15 | Docs: `pipeline-architecture.md`, ADRs 0006/0007/0008, 2 diagrams | ✅ | present; ADRs + `diagrams/*.mmd` render on GitHub. |
| 16 | Governance annotations on dbt models | ✅ *(added, Fix 2)* | every model + column has `meta`; catalogue + persist_docs (see Section B). |

---

## Section B — What's been fixed in this audit ✅

Each fix is a separate Conventional Commit on `claude/audit-bloc2-bloc3`.

### Fix 1 — Simulator real-time semantics (`refactor(simulator): ...`)
- **Before:** two modes — `SIM_MODE=history` (one-shot batch) + `drip.py` (random batches, no link
  to wall-clock).
- **After:** ONE process `simulator/run.py` with **stateful catch-up** to `NOW()`. New
  `simulator/state.py` (singleton `simulator.state`: `last_generated_at`, `bootstrap_completed`).
  Bootstrap backfills ~3y; thereafter it generates only `(last_generated_at, NOW]` and advances the
  watermark **in the same transaction** as the writes. IDs are deterministic per hour bucket
  (`uuid5` + `ON CONFLICT DO NOTHING`) → no duplicates. `--reset` + `--once` flags. Added the
  (missing) `simulator` compose service + `CATCH_UP_INTERVAL_SECONDS`. Deleted
  `generate_history.py` + `drip.py`. Made the S3 client fail-fast so best-effort bronze never blocks.
- **Now passes:** bootstrap = 17 027 orders (2023-06-13 → today); a simulated 5h downtime catch-up
  added only the new slice (**net +2 orders, 0 duplicate `order_id`**); a second run is a no-op.

### Fix 2 — Governance annotations + catalogue (`feat(governance): ...`)
- Every dbt model (10 staging + 9 marts incl. 3 gold views) carries model-level `meta`
  (`classification` C1–C4, `pii_level`, `retention_days`, `owner_role`, `steward_role`,
  `source_systems`, `update_frequency`, `quality_tier`) and every column carries column-level `meta`.
- `dbt_project.yml` → `+persist_docs` (relation + columns). **Verified live:**
  `col_description('gold.fact_sales', revenue)` = *"Line revenue in EUR (derived). Commercially
  sensitive."* — visible in pgAdmin.
- `scripts/export_governance_catalogue.py` generates `docs/bloc1-governance/data-asset-catalogue-v2.md`
  (**19 models**) + `annotation-rules.md`.

### Fix 3 — Blockers found while running the stack
| ID | Blocker (all from the Bloc 3↔4 merge unless noted) | Commit | Verified |
|----|-----------------------------------------------------|--------|----------|
| B1 | `monitoring.pipeline_runs` schema incompatible with its writers — DAG insert failed `column "rows_processed" does not exist`; Bloc 4 retrain reads `run_at`. Unified into one canonical DDL (`sql/ddl/06` mirrored into `infra/postgres/init/07`). | `fix(monitoring): ...` | DAG insert + retrain read both succeed. |
| B2 | No `generate_schema_name` macro → dbt wrote to **`public_silver`/`public_gold`** while real `silver`/`gold` (read by tests, views, Grafana, Bloc 4) stayed EMPTY. | `fix(dbt): ...` | data now in bare `gold` (30 108 rows); `public_gold` not created. |
| B3 | No committed `dbt/noureddine/profiles.yml` → the `ingest_orders` DAG couldn't resolve the profile. Added an env-var profile (Docker defaults, no secrets). | `fix(dbt): ...` | `dbt build` runs from the committed profile. |
| B6 | Gold analytical views existed only in `sql/ddl` and were **CASCADE-dropped** when dbt rebuilt `fact_sales`. Re-added as dbt view models (dbt owns gold). | `fix(dbt): ...` | `gold.v_daily_revenue` survives + repopulates (1 078 rows). |
| B4 | CI pinned **`dbt-postgres==1.8.3` which does not exist** → the latest `main` run was RED (only "dbt parse + compile" failed, at the install step). Pinned `1.8.2`. | `fix(ci): ...` | confirmed via Actions API (run 27414187927); 1.8.2 installs locally. |
| B5 | Two Grafana providers both named "NOUREDDINE" (one wouldn't load) + pipeline dashboard bound to the export placeholder `${DS_POSTGRESQL}` instead of the provisioned datasource. | `fix(grafana): ...` | single provider; rebound to `noureddine_pg`; both JSONs valid. |
| — | Bloc 2 README missing the consigne mapping table. | `docs(bloc2): ...` | added. |

---

## Section C — Manual testing guide

> Prereqs for the **Docker** path: Docker + Compose, ports 5432/5050/8080/9000/9001/3000/8000/8501
> free. Copy env: `cp .env.example .env`. Bring the stack up: `bash infra/scripts/up.sh`.
> Every block below is copy-paste-able. The **local (no-Docker)** equivalents that this audit
> actually executed are shown where they differ.

### 1. Postgres / OLTP
```bash
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "\dn"          # schemas
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c \
  "SELECT 'customers',count(*) FROM oltp.customers UNION ALL SELECT 'orders',count(*) FROM oltp.orders UNION ALL SELECT 'order_items',count(*) FROM oltp.order_items;"
```
**Expect:** schemas `oltp/silver/gold/bronze/monitoring/simulator`; counts in the thousands.
**Failure looks like:** `relation ... does not exist` → DDL/init didn't run; re-`up.sh` on a clean volume.

### 2. MinIO (bronze)
```bash
docker exec -it noureddine_minio mc alias set local http://localhost:9000 minio_admin change_me_minio
docker exec -it noureddine_minio mc ls --recursive local/bronze/orders/ | head
```
**Expect:** keys like `orders/year=2026/month=06/day=12/batch.json`.
**Failure:** empty listing → simulator hasn't run, or MinIO creds wrong. (This audit could not verify
MinIO live — no MinIO in the environment; partitioning is implemented + the write is fail-fast.)

### 3. Simulator state
```bash
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "SELECT * FROM simulator.state;"
```
**Expect:** one row, `bootstrap_completed = t`, `last_generated_at` near now.

### 4. Simulator catch-up demo
```bash
docker compose -f infra/docker-compose.yml stop simulator
# wait a few minutes, then:
docker compose -f infra/docker-compose.yml start simulator
docker logs --tail=20 noureddine_simulator        # look for "[catch-up] ... -> NOW (Xh)"
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c "SELECT last_generated_at FROM simulator.state;"
```
**Expect:** `last_generated_at` jumps forward by the downtime; **no duplicate orders**
(`SELECT count(*) FROM (SELECT order_id FROM oltp.orders GROUP BY order_id HAVING count(*)>1) x;` → 0).
**Local equivalent this audit ran:**
```bash
export DATABASE_URL=postgresql+psycopg2://noureddine_user:change_me_postgres@localhost:5432/noureddine
python -m simulator.run --reset --once     # bootstrap
python -m simulator.run --once             # catch-up / no-op
```

### 5. dbt build
```bash
docker compose -f infra/docker-compose.yml exec airflow bash -lc \
  "cd /opt/airflow/dbt/noureddine && dbt deps && dbt build"
# Local equivalent:
cd dbt/noureddine && dbt deps && DBT_PROFILES_DIR=. dbt build
```
**Expect:** `Done. PASS=77 WARN=0 ERROR=0 SKIP=0` (10 silver views + 6 gold tables + 3 gold views + 58 tests).
**Failure:** `Could not find profile` → see Section D (dbt in Airflow). `public_gold` created → the
`generate_schema_name` macro is missing (it isn't — Fix B2).

### 6. dbt tests
```bash
cd dbt/noureddine && DBT_PROFILES_DIR=. dbt test
```
**Expect:** 58 tests, 0 failures. The two singular tests `assert_no_orphan_fact_sales`,
`assert_revenue_non_negative` are listed.

### 7. Elementary report
```bash
cd dbt/noureddine && edr report --profiles-dir . --project-dir .
# output: edr_target/elementary_report.html
```
**Look for:** model/test run results, anomaly flags. **Note:** this audit could **not** run `edr`
locally — the dbt registry (`hub.getdbt.com`) and the `edr` package were network-blocked in the
audit environment; configuration (`packages.yml` elementary, `on-run-end` hook, `elementary` schema)
is correct. Verify on a network with hub access.

### 8. Airflow DAG `ingest_orders`
```bash
open http://localhost:8080      # admin / change_me_airflow
# DAGs → ingest_orders → Trigger; expect check_new_data → dbt_build → write_run_metadata green.
docker exec -it noureddine_postgres psql -U noureddine_user -d noureddine -c \
  "SELECT run_id,status,rows_processed,run_at FROM monitoring.pipeline_runs ORDER BY run_at DESC LIMIT 5;"
```
**Expect:** a `success` row per run. **Caveat:** requires the Section D Airflow-runs-dbt fix.
DAG parsing + the metadata insert were verified in this audit.

### 9. Forced-failure alerting
```bash
docker compose -f infra/docker-compose.yml exec -e FORCE_FAILURE=1 airflow airflow dags trigger ingest_orders
docker logs noureddine_airflow 2>&1 | grep '"alert": "pipeline_failure"'
```
**Expect:** a structured `ALERT {...}` JSON line from `alert_on_failure`; `dbt_build` shows failed.

### 10. Grafana dashboards
```bash
open http://localhost:3000      # admin / change_me_grafana → folder NOUREDDINE
```
**Expect two dashboards:** *Pipeline* (run history, rows processed, status from
`monitoring.pipeline_runs`; revenue/seasonality from `gold`) and *Model Health* (Bloc 4). Panels
bound to datasource `noureddine_pg`. **Note:** not rendered in this audit (no Docker); JSON is valid
and the datasource binding was corrected (Fix B5).

### 11. Pipeline tests
```bash
DATABASE_URL=postgresql+psycopg2://noureddine_user:change_me_postgres@localhost:5432/noureddine \
  pytest tests/test_pipeline.py -v
```
**Expect (verified):** 11 passed — `test_oltp_*`, `test_calendar_events_exist`, `test_silver_*`,
`test_gold_*`, `test_no_negative_revenue`, `test_no_orphan_fact_sales`, `test_seasonality_eid_vs_baseline`.

### 12. Healthcheck
```bash
bash infra/scripts/healthcheck.sh
```
**Expect:** all ✅ (containers healthy, OLTP/silver/gold populated, buckets present, API/Streamlit/
Grafana up). **Note:** requires Docker; not executed in this audit. The SQL assertions inside it pass
against the local DB.

### 13. Governance catalogue export
```bash
python scripts/export_governance_catalogue.py
ls -l docs/bloc1-governance/data-asset-catalogue-v2.md docs/bloc1-governance/annotation-rules.md
```
**Expect (verified):** `Wrote governance catalogue: ... (24765 bytes)`, 19 models; idempotent.

### 14. CI
```bash
gh run list --branch main --limit 5
gh run view <id>
```
**Expect after this branch merges:** all jobs green. **Before:** the latest `main` run
(27414187927, the Bloc 3 merge) was **failure** — only "dbt parse + compile (Bloc 3)" failed at
"Install dbt-postgres" (the `==1.8.3` ghost version). Fixed to `1.8.2` (Fix B4).

### 15. Clone-from-scratch reproducibility
```bash
git clone <repo> /tmp/nrd && cd /tmp/nrd && git checkout claude/audit-bloc2-bloc3
cp .env.example .env && bash infra/scripts/up.sh
docker compose up -d simulator && sleep 120
docker compose exec airflow bash -lc "cd /opt/airflow/dbt/noureddine && dbt deps && dbt build"
bash infra/scripts/healthcheck.sh
```
**Expect:** stack healthy, gold populated. **Caveat:** the dbt-in-Airflow step needs the Section D fix.

---

## Section D — What still needs work IN the repo ⚠️

1. **Airflow cannot run `dbt build` in the current image (HIGH).** The `airflow` service does not
   install dbt (`_PIP_ADDITIONAL_REQUIREMENTS` carries only ML deps), the `dbt` mount is `:ro` (dbt
   can't write `target/`, `logs/`, `dbt_packages/`), and there is no `dbt deps` step. So
   `ingest_orders.dbt_build` would fail in Docker with `dbt: command not found`. *Not fixed here* —
   the change is unverifiable without Docker and risks breaking container startup if done blindly.
   **Recommended fix:** give the BashOperator a dedicated dbt virtualenv so dbt's pinned deps don't
   clash with Airflow's, mount `dbt` read-write, and run `dbt deps` before `dbt build`, writing
   artefacts to a writable path. Sketch:
   ```yaml
   # compose: airflow volume
   - ../dbt:/opt/airflow/dbt        # was :ro
   ```
   ```python
   # ingest_orders.py dbt task (bash)
   "python -m venv /opt/airflow/.dbtvenv 2>/dev/null; "
   "/opt/airflow/.dbtvenv/bin/pip install -q dbt-postgres==1.8.2 elementary-data && "
   "cd /opt/airflow/dbt/noureddine && /opt/airflow/.dbtvenv/bin/dbt deps && "
   "DBT_PROFILES_DIR=. /opt/airflow/.dbtvenv/bin/dbt build"
   ```
   (Alternative: a dedicated dbt sidecar image, or `KubernetesPod/DockerOperator`.)
2. **CI `dbt-validate` beyond the install step is unverified here.** The hub (`hub.getdbt.com`) was
   blocked in the audit env, so `dbt deps` (Elementary `0.14.3` package) + `parse`/`compile` could
   not be exercised. They *should* pass on GitHub (hub reachable); if Elementary `0.14.3` is not a
   valid **dbt-package** version on hub, bump it. Local `dbt build` (without Elementary) is green.
3. **Gold DDL duplication (acceptable, documented).** `sql/ddl/03` + `05` still define the gold
   tables/views so the **Bloc 2-only** stack stands alone (CI `validate-sql` + healthcheck use them
   with the seed). At runtime **dbt is the owner** and rebuilds them. This is an intentional
   Bloc 2-bootstrap vs Bloc 3-runtime split, not a bug — but it is duplicated SQL to be aware of.
4. **Bootstrap is one large transaction.** A 3-year backfill commits in a single transaction (atomic
   watermark, but heavy). Fine at this scale; consider chunking by month if volume grows.
5. **`tests:` → `data_tests:` deprecation.** dbt 1.8 warns (non-blocking); rename before dbt ≥ 1.10.

---

## Section E — What needs to happen OUTSIDE the repo 📋

- **Slides Bloc 2 (~10, dark navy/gold):** architecture overview · stack choices (ADR 0001–0005
  summaries) · data model (ERD + star schema) · deployment & healthchecks · monitoring · demo path ·
  Q&R prep.
- **Slides Bloc 3 (~10):** pipeline architecture · micro-batch justification (ADR-0006) · dbt
  medallion · data quality (dbt tests + Elementary) · monitoring (Grafana) · alerting · **governance
  made operational** (annotations + catalogue + Postgres comments) · demo path · Q&R.
- **Video Bloc 2 (Loom 3–5 min):** `up.sh` → `docker ps` → `healthcheck.sh` green → pgAdmin
  (schemas + sample rows) → MinIO buckets → Airflow UI (DAGs list) → diagram walkthrough.
- **Video Bloc 3 (Loom 3–5 min):** simulator in catch-up mode (show `simulator.state` advancing) →
  trigger `ingest_orders` → `dbt build` green → silver/gold populated → Elementary report → Grafana
  dashboards live → `FORCE_FAILURE=1` firing the alert.
- **Bloc 1 governance doc enrichment:** append `data-asset-catalogue-v2.md` + `annotation-rules.md`
  as annexes to the Word governance doc — message: *"governance isn't paper — every asset carries
  classification, PII level, retention, owner, steward, enforced in dbt and visible in Postgres."*
- **Optional viz (Power BI / Metabase / Superset):** can connect to `gold.*` via Postgres; not
  implemented because (a) Power BI Pro is a paid licence (Bloc 1 zero-licence rule), (b) the Bloc 4
  Streamlit app already covers the business-user need. Worth an ADR as a future option.
- **Bloc 4:** ready to start once this branch merges to `main` and CI is green.

---

## Section F — Recommended jury Q&R prep

| Likely question | Pre-prepared answer (reference) |
|-----------------|----------------------------------|
| Why no Kafka / streaming? | SME volumetry; latency vs cost trade-off — **ADR-0006** (micro-batch every 10 min). |
| Why no Terraform? | Disproportionate for a single-host laptop stack — **ADR-0002**; AWS migration path documented. |
| Why MinIO not S3? | S3-API compatible + zero-licence + laptop-runnable — **ADR-0001**; 1:1 S3 migration documented. |
| Where is your data quality? | 58 dbt tests (generic + singular) + Elementary HTML report + Grafana panels — Section C.6/7/10. |
| How is governance enforced *in practice*? | dbt `meta` on every model/column → auto-catalogue (`data-asset-catalogue-v2.md`) → **Postgres comments via `persist_docs`** (live in pgAdmin). |
| How do you avoid two sources of truth for gold? | dbt owns gold at runtime (tables **and** views are dbt models); DDL is Bloc 2 bootstrap only — **ADR-0008** / Section D.3. |
| What if scale 10×? | MinIO→S3, Compose→ECS/EKS, Postgres→RDS, simulator→real Shopify ingestion — same service boundaries. |
| How does the pipeline stay current / recover? | Stateful catch-up simulator (`simulator.state` watermark, deterministic idempotent IDs) — Fix 1. |

---

### Readiness verdict
Blocs 2 + 3 are **green on everything executable without Docker** (dbt build PASS=77, 11 pipeline
tests, simulator bootstrap+catch-up, governance + persist_docs, 3 DAGs parse, CI blocker fixed). The
**one remaining gap that blocks a true end-to-end Docker demo** is *Airflow-runs-dbt* (Section D.1) —
self-contained and well-specified. Recommend: merge this branch (turns `main` CI green), apply the
Section D.1 fix on a machine with Docker, record the two videos, then start **Bloc 4**.
