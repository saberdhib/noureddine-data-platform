# ADR-0011 — Evidently for model monitoring

**Date:** 2026-06-12
**Status:** Accepted

## Context

A forecasting model in production degrades silently as demand patterns shift (a new event, a channel change, a stock-out distorting actuals). Bloc 1 governance and the DPIA #2 commitment require the model to be observable and to have a defined response when it drifts. We need data-drift detection on input features, target drift (actual vs predicted), and recurring performance scoring — feeding the existing Bloc 3 Grafana dashboard, not a parallel tool.

## Decision

**Evidently** computes monitoring artefacts inside the `monitor_model` Airflow DAG (daily):
- **Data drift** on input features + **target drift** (actual vs predicted), exported as a weekly HTML report.
- **Performance**: MAPE / RMSE recomputed on the last 30 days of actuals.
- **Key metrics** written to `monitoring.model_metrics` in Postgres → Grafana **"Model Health"** panel (drift score, MAPE, last training timestamp), extending the Bloc 3 dashboard.
- **Thresholds** (env-configurable): `DRIFT_THRESHOLD=0.5`, `MAPE_THRESHOLD=0.30`. A breach triggers the `retrain_model` DAG.

Monitoring code lives in `monitoring/evidently/`.

## Consequences

- ✅ **Zero-licence, Python-native**: integrates directly in Airflow tasks; no extra service.
- ✅ **Closed loop**: thresholds turn drift into an automated retraining trigger (see ADR-0013 / retraining flow), giving an auditable, governed response to degradation.
- ✅ **One pane of glass**: metrics land in the same Postgres → Grafana stack from Bloc 3; no tool sprawl. Monitoring stays in Grafana; Streamlit stays business-only.
- ✅ **DPIA #2**: HTML reports + Grafana history provide the evidence trail for the AI-forecasting risk assessment.
- ⚠️ **Report storage**: HTML reports accumulate; retention is bounded by keeping the latest and gitignoring the rest.

## Alternatives considered

- **Hand-rolled drift checks** — duplicates well-tested Evidently statistics, more code to defend; rejected.
- **Prometheus + custom exporters** — adds another runtime for metrics already expressible in Postgres + Grafana; disproportionate.
- **NannyML / WhyLabs / Arize** — heavier or SaaS-leaning; conflict with the zero-licence, laptop-runnable constraint; rejected.
