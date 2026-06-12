# Grafana — Observability (Bloc 3 + Bloc 4)

Grafana provides the platform's **operational** observability. It is provisioned
automatically from this folder when the `grafana` compose service starts.

```
infra/grafana/
├── provisioning/
│   ├── datasources/postgres.yml      # NOUREDDINE-Postgres datasource (uid: noureddine_pg)
│   └── dashboards/dashboards.yml     # loads JSON dashboards from /var/lib/grafana/dashboards
├── dashboards/
│   └── model_health.json             # Bloc 4 — "Model Health" dashboard
└── README.md
```

## "Model Health" dashboard (Bloc 4)

Queries `monitoring.model_metrics` and `monitoring.retrain_events`:

| Panel | Source | Meaning |
|-------|--------|---------|
| Latest drift score (gauge) | `model_metrics.drift_score` | green < 0.3, orange ≥ 0.3, red ≥ 0.5 (DRIFT_THRESHOLD) |
| Latest MAPE (stat) | `model_metrics.mape` | red ≥ 0.30 (MAPE_THRESHOLD) |
| Last drift report (stat) | `model_metrics.measured_at` | freshness of monitoring |
| Last training (stat) | `retrain_events.occurred_at` (promoted) | last promotion timestamp |
| MAPE over time (timeseries) | `model_metrics` | performance trend |
| Drift score over time (timeseries) | `model_metrics` | input-drift trend |
| Retraining events (table) | `retrain_events` | promote / no-promote audit trail |

This **extends** the Bloc 3 pipeline-health observability (`monitoring.pipeline_runs`)
rather than replacing it — both live in the same Grafana instance and Postgres
datasource. Monitoring stays here and in Evidently; the Streamlit app is business
only (separation of concerns).

## Access

- URL: http://localhost:3000  (default user `admin`, password from `GRAFANA_ADMIN_PASSWORD`).
- The dashboard appears under the **NOUREDDINE** folder.

## Credentials / env

The datasource reads its connection from env vars injected by compose
(`NOUREDDINE_DB_HOST/NAME/USER/PASSWORD`). No secrets are committed.
