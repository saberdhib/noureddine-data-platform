# `ml/` — Demand Forecasting (Bloc 4)

LightGBM model that forecasts **daily units sold per category** (category × day,
horizon 30 days), driven by Islamic-calendar features. **No PII** in features (DPIA #2).

```
ml/
├── src/
│   ├── config.py     # DB engine + model paths + constants
│   ├── features.py   # calendar + lag + rolling features (assert_no_pii)
│   ├── train.py      # pull gold.fact_sales -> features -> train/validate -> save + SHAP
│   ├── predict.py    # load current.pkl -> recursive 30d forecast (date, prediction, lower, upper)
│   ├── retrain.py    # train -> MAPE gate -> atomic promote / hold -> keep last 5
│   └── model_card.py # metrics + SHAP -> docs/bloc4-ai-mlops/model-card.md
├── scripts/
│   └── generate_demo_data.py  # synthetic warehouse fixture (stand-in for Bloc 3 output, ADR-0014)
├── tests/            # synthetic, DB-free unit tests (CI)
├── notebooks/        # EDA / feature analysis (consigne /notebooks)
├── retrain/          # retraining docs (consigne /retrain)
├── models/           # current.pkl (symlink), metrics.json, shap_summary.png, model_card.md
└── requirements.txt
```

## Quick start (local)

```bash
pip install -r ml/requirements.txt
export POSTGRES_HOST=localhost POSTGRES_USER=noureddine_user POSTGRES_PASSWORD=... POSTGRES_DB=noureddine
# If gold.fact_sales is empty (no Bloc 3 output yet), seed the demo fixture:
python ml/scripts/generate_demo_data.py
# Train (writes ml/models/current.pkl, metrics.json, shap_summary.png):
python ml/src/train.py
# One-day forecast for a category:
python ml/src/predict.py Qamis
```

## Governance

`features.assert_no_pii` rejects any individual-level column; `tests/test_features.py`
enforces it. Calendar features come only from `oltp.calendar_events` (fixed windows —
Hijri dates are never recomputed). See `docs/bloc4-ai-mlops/model-card.md`.
