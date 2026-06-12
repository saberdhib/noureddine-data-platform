# Evidently — Model Monitoring (Bloc 4)

This sibling of the Bloc 3 Grafana setup adds **model** monitoring on top of the
existing **pipeline** monitoring. Monitoring stays out of the business Streamlit
app by design (separation of concerns).

## What it does

`generate_report.py`:

1. Loads the promoted model (`ml/models/current.pkl`).
2. Builds two windows of features + 1-step-ahead predictions:
   - **reference** — the 90 days preceding the current window (the recent learned
     distribution; the training-data snapshot persisted at `ml/models/training_data_snapshot.parquet`
     is the documented training baseline).
   - **current** — the last 30 days of actuals + predictions.
3. Generates an **Evidently HTML report** (`DataDriftPreset` + `RegressionPreset`)
   under `reports/report_{timestamp}.html`.
4. Computes and stores key metrics in `monitoring.model_metrics`:
   - `drift_score` — share of **demand-level** features (lags + rolling means) that
     drifted. Deterministic calendar/time features are intentionally excluded
     (they always differ window-to-window), and a feature only counts as drifted
     when the KS test is significant **and** the mean shift exceeds 30% — this
     keeps seasonal noise from producing false alarms.
   - `target_drift`, `mape`, `rmse`, `model_version`, `report_path`, `breached`.

## Thresholds → retrain trigger

Env-configurable (defaults in `.env.example`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `DRIFT_THRESHOLD` | `0.5` | breach if `drift_score >= DRIFT_THRESHOLD` |
| `MAPE_THRESHOLD`  | `0.30`| breach if current `mape >= MAPE_THRESHOLD` |

When a row is written with `breached = true`, the daily `monitor_model` Airflow
DAG triggers `retrain_model` via `TriggerDagRunOperator`.

## Running

```bash
# nominal weekly run (writes a fresh model_metrics row + HTML report)
python monitoring/evidently/generate_report.py

# demo: deliberately trip the drift detector to show the retrain trigger
python monitoring/evidently/generate_report.py --force-drift
```

## Viewing

Open the latest `reports/report_*.html` in a browser. Reports are gitignored
(only this README is tracked) because they are large generated artefacts; the
**numeric** metrics live in Postgres and are surfaced on the Grafana
**"Model Health"** panel.
