"""Train the LightGBM demand-forecasting model (Bloc 4).

Pulls aggregate ``gold.fact_sales`` (units per category per day) + the governed
``oltp.calendar_events`` windows, builds calendar/lag/rolling features (NO PII),
does a time-based split (last 30 days held out), trains LightGBM, computes
MAPE/sMAPE/RMSE per category and globally, then trains a final production model
on the full history. Saves a timestamped bundle, a SHAP summary plot, a metrics
JSON and a snapshot of the training matrix (used later by Evidently).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import shap  # noqa: E402
from sqlalchemy import text  # noqa: E402

from config import (METRICS_FILE, MODELS_DIR, SHAP_FILE, SNAPSHOT_FILE,  # noqa: E402
                    VALIDATION_DAYS, get_engine)
from features import (FEATURE_COLUMNS, TARGET, assert_no_pii,  # noqa: E402
                      build_training_matrix)

LGB_PARAMS = dict(objective="regression", metric="rmse", n_estimators=400,
                  learning_rate=0.05, num_leaves=31, min_child_samples=20,
                  subsample=0.9, colsample_bytree=0.9, random_state=42, n_jobs=-1)


def load_daily_demand(engine) -> pd.DataFrame:
    """Aggregate fact_sales to daily units per category. No PII columns selected."""
    sql = text("""
        SELECT d.date AS date, p.category AS category, SUM(f.quantity)::float AS units
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON d.date_key = f.date_key
        JOIN gold.dim_product p ON p.product_key = f.product_key
        GROUP BY d.date, p.category
        ORDER BY d.date, p.category
    """)
    return pd.read_sql(sql, engine)


def load_calendar(engine) -> pd.DataFrame:
    return pd.read_sql(text(
        "SELECT event_name, event_type, start_date, end_date FROM oltp.calendar_events"), engine)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    denom = np.where(y_true == 0, np.nan, y_true)
    mape = float(np.nanmean(np.abs((y_true - y_pred) / denom)))
    smape = float(np.mean(np.abs(y_true - y_pred) / ((np.abs(y_true) + np.abs(y_pred)) / 2 + 1e-9)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    return {"mape": round(mape, 4), "smape": round(smape, 4), "rmse": round(rmse, 4)}


def train(save: bool = True, promote: bool = True) -> dict:
    engine = get_engine()
    daily = load_daily_demand(engine)
    calendar = load_calendar(engine)
    if daily.empty:
        raise RuntimeError("gold.fact_sales produced no rows — run the data pipeline first.")

    X, y, feat_names, frame, categories = build_training_matrix(daily, calendar)
    assert_no_pii(X)

    # Time-based split: last VALIDATION_DAYS days are validation.
    max_date = frame["date"].max()
    split_date = max_date - pd.Timedelta(days=VALIDATION_DAYS)
    train_mask = frame["date"] <= split_date
    val_mask = frame["date"] > split_date

    model = lgb.LGBMRegressor(**LGB_PARAMS)
    model.fit(X[train_mask], y[train_mask], categorical_feature=["category_code"])

    # Validation metrics (global + per category).
    val_frame = frame[val_mask].copy()
    val_frame["pred"] = np.clip(model.predict(X[val_mask]), 0, None)
    global_metrics = _metrics(val_frame[TARGET], val_frame["pred"])
    per_category, rmse_per_category = {}, {}
    for cat in categories:
        sub = val_frame[val_frame["category"] == cat]
        if len(sub):
            m = _metrics(sub[TARGET], sub["pred"])
            per_category[cat] = m
            rmse_per_category[cat] = m["rmse"]

    # Final production model on the full history.
    final = lgb.LGBMRegressor(**LGB_PARAMS)
    final.fit(X, y, categorical_feature=["category_code"])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    bundle = {
        "model": final,
        "feature_names": feat_names,
        "categories": categories,
        "rmse_per_category": rmse_per_category,
        "global_rmse": global_metrics["rmse"],
        "metrics": {"global": global_metrics, "per_category": per_category},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "version": timestamp,
        "n_train_rows": int(train_mask.sum()),
        "n_observations": int(len(frame)),
        "target": TARGET,
    }

    metrics_doc = {
        "version": timestamp, "trained_at": bundle["trained_at"],
        "global": global_metrics, "per_category": per_category,
        "categories": categories, "feature_names": feat_names,
        "n_observations": int(len(frame)),
        "date_range": [str(frame["date"].min().date()), str(frame["date"].max().date())],
    }

    if save:
        model_path = MODELS_DIR / f"model_{timestamp}.pkl"
        joblib.dump(bundle, model_path)
        metrics_doc["model_path"] = str(model_path)
        METRICS_FILE.write_text(json.dumps(metrics_doc, indent=2))
        _save_shap(final, X.sample(min(2000, len(X)), random_state=0))
        frame.to_parquet(SNAPSHOT_FILE, index=False)
        if promote:
            _atomic_promote(model_path)
            print(f"Saved {model_path.name}; promoted current.pkl; global={global_metrics}")
        else:
            print(f"Saved candidate {model_path.name} (not promoted); global={global_metrics}")

    return metrics_doc


def _atomic_promote(model_path):
    """Atomically point current.pkl at a freshly written, load-tested bundle."""
    from config import CURRENT_MODEL
    joblib.load(model_path)  # load-test before promoting
    tmp = CURRENT_MODEL.with_suffix(".pkl.tmp")
    if tmp.exists() or tmp.is_symlink():
        tmp.unlink()
    tmp.symlink_to(model_path.name)  # relative symlink within models/
    tmp.replace(CURRENT_MODEL)       # atomic rename over current.pkl


def _save_shap(model, X_sample):
    try:
        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(X_sample)
        plt.figure()
        shap.summary_plot(sv, X_sample, show=False, plot_size=(9, 6))
        plt.tight_layout()
        plt.savefig(SHAP_FILE, dpi=110, bbox_inches="tight")
        plt.close("all")
        print(f"SHAP summary saved -> {SHAP_FILE}")
    except Exception as exc:  # pragma: no cover - SHAP plotting is best-effort
        print(f"WARNING: SHAP plot failed ({exc}); continuing.")


if __name__ == "__main__":
    train()
