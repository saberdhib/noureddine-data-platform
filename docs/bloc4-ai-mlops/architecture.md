# Architecture — Bloc 4 (AI / MLOps)

> Logical and technical architecture of the forecasting, serving, monitoring and retraining
> layer. Builds directly on the governed warehouse (Bloc 2) and the pipelines (Bloc 3).
> Diagrams: [ml-pipeline.mmd](diagrams/ml-pipeline.mmd),
> [serving-architecture.mmd](diagrams/serving-architecture.mmd),
> [retraining-flow.mmd](diagrams/retraining-flow.mmd).

---

## 1. End-to-end data flow

```
gold.fact_sales  +  oltp.calendar_events
            │
            ▼
   Feature engineering  (no PII — aggregate per category)
   ─ Calendar windows: days_to_next_eid_fitr / _adha, days_to_ramadan_start,
     days_to_black_friday, in_ramadan, in_pre_eid_window (14d), in_nikah_season,
     is_weekend, day_of_week, month, week_of_year  (fixed Bloc 3 windows, never recomputed)
   ─ Lags per category: lag_7, lag_14, lag_30
   ─ Rolling means per category: rolling_7d, rolling_30d
   ─ category as native LightGBM categorical
            │
            ▼
   LightGBM train / validate
   ─ Time-based split, last 30 days held out
   ─ Metrics: MAPE, sMAPE, RMSE — per category + global
   ─ SHAP global summary → ml/models/shap_summary.png
            │
            ▼
   Atomic model promotion
   ─ Write ml/models/{name}_{timestamp}.pkl
   ─ Swap symlink ml/models/current.pkl  (never serve a half-written model)
   ─ Keep last 5 versions for rollback
            │
            ▼
   FastAPI serving   ── X-API-Key auth on /predict and /retrain
            │
            ▼
   Streamlit business app  (3 pages — calls FastAPI for forecasts,
                            read-only Postgres for gold + inventory + calendar)
            │
            ▼
   Evidently monitoring  ──▶  monitoring.model_metrics  ──▶  Grafana "Model Health"
            │
            ▼
   Drift-triggered retrain
   ─ monitor_model (daily) → check_thresholds → TriggerDagRunOperator → retrain_model
```

The corresponding flowchart is [diagrams/ml-pipeline.mmd](diagrams/ml-pipeline.mmd).

---

## 2. Feature engineering (governed, PII-free)

Per **DPIA #2**, the model never sees personal data. The training matrix is built from
**aggregate per-category daily demand** joined to **calendar context**:

- **Source of truth:** `gold.fact_sales` (quantities, revenue, dates, category via `dim_product`)
  aggregated to one row per `category × day`.
- **Calendar features** are derived from `oltp.calendar_events`, reusing the **same fixed windows
  defined in Bloc 3** — Hijri dates are *never* recomputed here, guaranteeing consistency between
  pipelines and model.
- **Autoregressive features** (lags, rolling means) are computed *within each category* so the
  model captures momentum without leaking across categories.
- `category` is passed as a **native LightGBM categorical** feature (no one-hot blow-up).

A test asserts that **no `customer_id` / PII column** can enter the feature set (DPIA #2 control).

---

## 3. Training and validation

- **Algorithm:** LightGBM regression (see [ADR-0009](adrs/0009-lightgbm-over-prophet.md)).
- **Split:** strictly **time-based**. The **last 30 days** are held out as the validation horizon —
  this mirrors the production task (predict the next 30 days) and prevents look-ahead leakage.
- **Metrics:** MAPE, sMAPE, RMSE, computed **per category and globally**. The global MAPE is the
  acceptance gate (target ≤ 30 %, `MAPE_THRESHOLD=0.30`).
- **Explainability:** a SHAP global summary plot is written to `ml/models/shap_summary.png` and
  embedded in the (code-generated) model card — the DPIA #2 transparency commitment.

---

## 4. Atomic model promotion

To guarantee serving never reads a partial artifact:

1. Train and serialise to `ml/models/{name}_{timestamp}.pkl`.
2. Validate on the held-out 30 days.
3. **Promote** only if `new_MAPE ≤ current_MAPE × 1.05`; otherwise **hold** and log a
   `"no-promotion"` event (the current model keeps serving).
4. Promotion is an **atomic symlink swap** of `ml/models/current.pkl` onto the new file.
5. The last **5** versions are retained for rollback; older ones are gitignored.

FastAPI always loads `current.pkl`, so promotion is transparent to callers.

---

## 5. Serving — FastAPI

See [ADR-0010](adrs/0010-fastapi-for-serving.md) and
[diagrams/serving-architecture.mmd](diagrams/serving-architecture.mmd).

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | open | Liveness probe. |
| `/model-info` | GET | open | Current model name, timestamp, metrics. |
| `/predict` | POST | **X-API-Key** | Input `{category, horizon ≤ 30}` → list of `{date, prediction, lower, upper}`. |
| `/retrain` | POST | **X-API-Key (admin)** | Human-in-the-loop trigger of a retrain. |

- **Auth:** API key via env var, header **`X-API-Key`** (governance P-03 spirit). `/health` and
  `/model-info` are open; `/predict` and `/retrain` require the key.
- **Docs:** OpenAPI UI at `/docs`. Container exposes internal port **8000**.
- **Read path:** FastAPI reads `gold` for the context it needs to build prediction inputs; it loads
  the model from `current.pkl`.

---

## 6. Business app — Streamlit (3 pages)

See [ADR-0012](adrs/0012-streamlit-for-business.md). The app is **business-only**; all monitoring
stays in Grafana — a deliberate separation of concerns.

- **Page 1 — Executive Dashboard:** KPIs from `gold` (revenue, orders, AOV, top categories, top
  channels) with a date-range filter.
- **Page 2 — Demand Forecast** ⭐ (the signature view): category × day chart, **J-90 history +
  J+30 prediction with confidence interval**, and **Islamic-calendar overlays drawn on the chart** —
  gold band for Ramadan, dashed vertical lines for Eid al-Fitr, a distinct colour for Eid al-Adha,
  a lighter band for Nikah season, a marker for Black Friday. Category filter in the sidebar.
- **Page 3 — Stock Pilot:** per-category table — current inventory, predicted 30-day demand,
  days of cover remaining, and a restock signal (🟢 / 🟠 / 🔴, env-configurable thresholds).

**Separation rule:** Streamlit **only calls FastAPI for predictions** — it never loads the model
directly. It holds a **read-only** Postgres connection for `gold` + inventory + calendar context.
Charts use Plotly (interactive, screencast-friendly).

---

## 7. Monitoring — Evidently → Postgres → Grafana

See [ADR-0011](adrs/0011-evidently-for-model-monitoring.md).

- **Drift report:** data drift on input features + target drift (actual vs predicted), weekly HTML
  under `monitoring/evidently/`.
- **Performance:** MAPE / RMSE recomputed weekly on the last 30 days of actuals.
- **Metrics export:** key metrics land in **`monitoring.model_metrics`** in Postgres, feeding the
  Grafana **"Model Health"** panel — this *extends* the Bloc 3 dashboard rather than creating a new
  one.
- **Thresholds** (env-configurable): `DRIFT_THRESHOLD=0.5`, `MAPE_THRESHOLD=0.30`. A breach is the
  trigger for retraining.

---

## 8. Retraining — dual-trigger orchestration

See [diagrams/retraining-flow.mmd](diagrams/retraining-flow.mmd).

- **Scheduled:** Airflow DAG **`retrain_model`** runs weekly (**Sundays 02:00**).
- **Drift-triggered:** DAG **`monitor_model`** runs **daily**, executes Evidently, and on a
  threshold breach fires `retrain_model` via Airflow's **`TriggerDagRunOperator`**.
- **Retrain process:** extract `gold.fact_sales` → feature engineering → train LightGBM →
  validate on the held-out 30 days → **promote** (if new MAPE ≤ current × 1.05) **or hold**.
- **Quality gate (P-04):** `retrain_model` checks the last `monitoring.pipeline_runs` status; if the
  upstream Bloc 3 dbt tests are red, training is **skipped** — the model never trains on bad data.

---

## 9. Governance ties (Bloc 1)

- **DPIA #2:** no `customer_id`, no PII in features; aggregate per-category demand only; model card
  published; SHAP for transparency; **human-in-the-loop** via the `/retrain` admin endpoint and the
  fact that Streamlit is **decision-support** (it never takes automated stock actions).
- **P-03:** protected endpoints require `X-API-Key`.
- **P-04:** quality gates guard the training data (no green dbt → no training).

---

## 10. Why these choices (defensible summary)

| Concern | Choice | Rationale | ADR |
|---------|--------|-----------|-----|
| Model | LightGBM | Fast on laptop, explainable (SHAP), strong on event-driven peaks. | 0009 |
| Serving | FastAPI | Async, OpenAPI, clean auth, mirrors real deployment. | 0010 |
| Monitoring | Evidently | Open-source drift + performance, HTML + metric export. | 0011 |
| Business UI | Streamlit | Fast Python BI, Plotly charts, calls the API (no model in UI). | 0012 |
| Orchestration scale | Docker Compose, **no K8s** | Disproportionate for a 30-FTE PME. | 0013 |
