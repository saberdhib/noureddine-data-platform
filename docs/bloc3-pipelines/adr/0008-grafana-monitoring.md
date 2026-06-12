# ADR 0008 — Grafana for pipeline monitoring + gold ownership handover

**Status:** Accepted  
**Date:** 2026-06-12  
**Deciders:** Student developer

## Part A — Grafana for pipeline monitoring

### Context

Bloc 3 requires a monitoring dashboard showing pipeline health (row counts, freshness, test pass-rate, run history). Options:

| Tool | Source | Cost | Complexity |
|------|--------|------|-----------|
| **Grafana** | PostgreSQL datasource | Free/OSS | Low (provisioned via JSON) |
| Metabase | PostgreSQL | Free (community) | Low |
| CloudWatch | AWS native | Paid (AWS) | Managed |
| Prometheus + Grafana | Metrics scraping | Free | Medium (requires Prometheus) |

### Decision

Use **Grafana 10.4.x** with a **PostgreSQL datasource only** (no Prometheus).

Dashboards are provisioned automatically via `infra/grafana/provisioning/` — no manual setup required.

The Airflow DAG writes run metadata into `monitoring.pipeline_runs` (a plain SQL table). Grafana queries it directly.

### Rationale

- Zero cost, self-hosted, laptop-runnable.
- PostgreSQL is already in the stack; no additional data store for metrics.
- Provisioned dashboards mean the demo is reproducible from `docker compose up`.
- In a real AWS production deployment the equivalent would be **CloudWatch** (native, managed, no additional infrastructure). CloudWatch is not deployed here to avoid AWS costs and stay laptop-runnable.

### Consequences

- Grafana is reusable in Bloc 4 for ML model monitoring (Evidently output → Postgres → Grafana).
- No Prometheus: this is a deliberate scope decision. Custom metrics are SQL, not time-series scrapes.

---

## Part B — Gold schema ownership handover (corrective)

### Context

In Bloc 2, the gold schema DDL was defined in `sql/ddl/03_create_tables_warehouse.sql`. From Bloc 3 onward, `dbt` builds the gold schema via mart models (`+materialized: table`, `+schema: gold`).

Having two sources of truth for schema `gold` is a governance violation (Bloc 1 P-04).

### Decision

From Bloc 3 onward, **dbt is the single owner of schema `gold`**. The Bloc 2 DDL file is annotated as superseded (comment added). dbt mart models are the canonical definition.

The Airflow DAG runs `dbt build` which drops and recreates gold tables on each run.

### Consequences

- If the Bloc 2 init SQL runs (fresh `docker compose up`), it creates empty gold tables that dbt immediately replaces. No conflict.
- The Bloc 2 DDL is kept for documentation purposes (annotated, not removed) so the Bloc 2 schema decisions remain traceable.
