# `monitoring/` — Model & Pipeline Observability (Bloc 4)

Monitoring lives here and in Grafana — **never** in the business Streamlit app.

```
monitoring/
├── evidently/         # model monitoring (drift + performance)
│   ├── generate_report.py   # Evidently HTML + metrics -> monitoring.model_metrics
│   ├── reports/             # generated HTML (gitignored, keep README/.gitkeep)
│   └── README.md
└── README.md
```

Grafana provisioning + the **"Model Health"** dashboard live under
`infra/grafana/` (datasource, dashboard provider, `model_health.json`).

## Flow

1. `monitor_model` DAG runs `evidently/generate_report.py` daily.
2. It compares the recent 30-day window against the preceding baseline, writes an
   Evidently HTML report and a row in `monitoring.model_metrics`
   (drift score, target drift, MAPE, RMSE, breach flag).
3. Grafana reads `monitoring.model_metrics` + `monitoring.retrain_events` for the
   "Model Health" panels.
4. A threshold breach (`DRIFT_THRESHOLD` / `MAPE_THRESHOLD`) makes `monitor_model`
   trigger `retrain_model`.

See `monitoring/evidently/README.md` and `infra/grafana/README.md` for details.
