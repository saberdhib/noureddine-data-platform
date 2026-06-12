# Bloc 4 — AI / MLOps & Business Consumption

> Demand forecasting and decision-support layer for the NOUREDDINE Data Platform.
> This bloc trains a model, serves it through an API, monitors it, retrains it on drift,
> and exposes the result to the business through a Streamlit application.

---

## 1. What this bloc delivers

Bloc 4 closes the platform: the governed warehouse built in Bloc 2 and the pipelines built
in Bloc 3 now feed a **machine-learning forecasting layer**.

- **Model:** **LightGBM** gradient-boosted regression.
- **Target:** daily number of orders, at **category × day** granularity.
- **Horizon:** **30 days** ahead.
- **Why it matters:** NOUREDDINE pilots a *limited stock against irregular, event-driven demand*.
  Peaks cluster around the **Islamic cultural calendar** (Ramadan, Eid al-Fitr, Eid al-Adha,
  Nikah season) plus retail events (Black Friday, Summer Sale). A governed forecast turns those
  known calendar windows into actionable restock signals.
- **Governance:** trained on **aggregate per-category demand only** — **no PII**, per DPIA #2.
  SHAP explainability and a published model card are part of that commitment.

The full set of LOCKED technical decisions lives in `CLAUDE.md` section 9; this README documents
the structure, the demo path, and how each *consigne* requirement maps onto the repo.

---

## 2. Consigne → repo mapping

The school *consigne* expects a flat `/notebooks /src /tests /models requirements.txt` (ML side)
and `/api /k8s /monitoring /retrain Dockerfile .github/workflows/` (deploy side). To keep the
mono-repo coherent (same corrective pattern used in Bloc 3), those folders map onto the existing
tree as follows:

| Consigne path | Repo location | Notes |
|---------------|---------------|-------|
| `/notebooks` | `ml/notebooks/` | Exploration, feature analysis, SHAP review. |
| `/src` | `ml/src/` | `train.py`, feature engineering, validation, promotion. |
| `/tests` | `ml/tests/` + `api/tests/` | ML unit/feature tests + API contract tests. |
| `/models` | `ml/models/` | Versioned `.pkl`, `current.pkl` symlink, `shap_summary.png`. |
| `requirements.txt` | **per service** (`ml/`, `api/`, `streamlit/`) | Decoupled dependency sets. |
| `/api` | `api/` | FastAPI serving app (`/health`, `/model-info`, `/predict`, `/retrain`). |
| `/k8s` | **NOT IMPLEMENTED** | Docker Compose suffices for a 30-FTE PME; K8s disproportionate. See [ADR-0013](adrs/0013-docker-compose-over-k8s.md). |
| `/monitoring` | `monitoring/evidently/` | Evidently reports; extends the Bloc 3 Grafana stack, not a new one. |
| `/retrain` | `ml/retrain/` + `dags/retrain_model.py` | Retrain logic + its Airflow DAG. |
| `Dockerfile` | **per service** (`api/`, `streamlit/`, ml image) | One image per concern. |
| `.github/workflows/` | already exists, **extended** | Adds `ml-test`, `api-test`, `streamlit-smoke`. |

---

## 3. Architecture in one paragraph

`gold.fact_sales` + `oltp.calendar_events` → **feature engineering** (calendar windows + lags +
rolling means, no PII) → **LightGBM** train/validate on a time split (last 30 days held out) →
**atomic promotion** of the winning model to `ml/models/current.pkl` → **FastAPI** serves
`/predict` behind an `X-API-Key` → **Streamlit** (3 business pages) consumes the API and the gold
layer → **Evidently** computes drift/performance into `monitoring.model_metrics` → **Grafana**
renders the "Model Health" panel → on threshold breach, `monitor_model` triggers `retrain_model`.
Full write-up in [architecture.md](architecture.md). Diagrams in [diagrams/](diagrams/).

---

## 4. How to demo

A clean walk-through for the screencast. Run from the repo root.

1. **Start the stack.** `docker compose -f infra/docker-compose.yml up -d` — Postgres, MinIO,
   Airflow, dbt, Grafana, FastAPI, Streamlit come up. Wait for health checks to go green.
2. **Confirm data is present.** Let the Bloc 3 simulator drip (or load the seed) so
   `gold.fact_sales` holds enough history (≥ 120 days recommended for lags + 30d holdout).
3. **Train the model.** `python ml/src/train.py` — extracts gold, builds features, trains LightGBM,
   validates on the last 30 days, writes a timestamped `.pkl`, swaps `current.pkl`, and saves
   `ml/models/shap_summary.png`.
4. **Start serving + app.** FastAPI on `:8000`, Streamlit on `:8501` (both via compose).
5. **Open the API docs.** Browse `http://localhost:8000/docs` (OpenAPI). Show `/health` and
   `/model-info` are open.
6. **Call `/predict`.** With the key:
   `curl -X POST http://localhost:8000/predict -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '{"category":"Qamis","horizon":30}'`
   → a 30-row list of `{date, prediction, lower, upper}`. Show that omitting the key returns 401/403.
7. **Trigger `retrain_model` in Airflow.** Open `http://localhost:8080`, run the DAG manually:
   extract → features → train → validate → **promote or hold** (promotes only if new MAPE ≤
   current × 1.05).
8. **Trigger `monitor_model`.** Run the daily monitoring DAG: Evidently computes drift + recomputed
   MAPE/RMSE on the last 30 days and writes to `monitoring.model_metrics`.
9. **Show the Evidently HTML report.** Open the generated report under `monitoring/evidently/` —
   data drift on input features and target drift (actual vs predicted).
10. **Show the Grafana "Model Health" panel.** Drift score, MAPE, last-training timestamp — live,
    extending the Bloc 3 dashboard.
11. **Walk the 3 Streamlit pages.** Executive Dashboard (KPIs) → **Demand Forecast** ⭐ (J-90 history
    + J+30 forecast with confidence band and the **Islamic-calendar overlays** — Ramadan gold band,
    Eid al-Fitr dashed lines, Eid al-Adha in a distinct colour, Nikah-season band, Black Friday
    marker) → Stock Pilot (days-of-cover + 🟢/🟠/🔴 restock signal) → **🤖 AI Advisor** (optional,
    ADR-0015): a grounded OpenAI briefing that turns forecast + inventory + **restock lead time**
    (`RESTOCK_LEAD_TIME_DAYS`) + calendar into an actionable restock plan in French — it flags
    *rupture avant livraison* (cover < lead time). Disabled unless `OPENAI_API_KEY` is set; only
    category-level aggregates are sent (no PII); shows the underlying data even without a key.

    **Punchy pre-Eid demo:** `python ml/scripts/seed_demo_pre_eid.py` then `python ml/src/train.py`
    seeds data ending ~14 days before Eid al-Adha 2026 with tight inventory. The pages auto-anchor on
    the data frontier (`db.data_today()`), so the forecast straddles the Eid spike and every Eid-driven
    category shows *rupture avant livraison* — the advisor recommends ordering now.
12. **Force a drift breach.** Inject an anomalous row (SQL) or lower a threshold via env override
    (`DRIFT_THRESHOLD` / `MAPE_THRESHOLD`), re-run `monitor_model`, and show it firing
    `TriggerDagRunOperator` → `retrain_model` automatically. This closes the MLOps loop on camera.

---

## 5. Environment note

The reference build was validated by running **PostgreSQL locally** and **training/serving the model
directly** against it (feature engineering, LightGBM training, atomic promotion, and FastAPI
`/predict` were exercised end-to-end). The **Docker-orchestrated services** (Airflow scheduler,
Grafana) are wired through `docker-compose` and validated by **configuration and import checks**
(DAG parsing, service config, provider imports) rather than a full live cluster run on the build
host. This keeps the bloc reproducible on a laptop while remaining honest about what was executed
live versus validated by configuration.

---

## 6. Contents

| File | Description |
|------|-------------|
| [cahier-des-charges.md](cahier-des-charges.md) | Business need, success criteria, constraints (FR). |
| [architecture.md](architecture.md) | Bloc 4 data flow, serving, monitoring, retraining. |
| [adrs/](adrs/) | Architecture Decision Records 0009–0013. |
| [diagrams/](diagrams/) | Mermaid sources: ML pipeline, serving, retraining. |

### ADR quick links

- [ADR-0009](adrs/0009-lightgbm-over-prophet.md): LightGBM over Prophet
- [ADR-0010](adrs/0010-fastapi-for-serving.md): FastAPI for model serving
- [ADR-0011](adrs/0011-evidently-for-model-monitoring.md): Evidently for model monitoring
- [ADR-0012](adrs/0012-streamlit-for-business.md): Streamlit for the business app
- [ADR-0013](adrs/0013-docker-compose-over-k8s.md): Docker Compose over Kubernetes
