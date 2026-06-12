"""Inference for the demand-forecasting model (Bloc 4).

Loads the promoted ``current.pkl`` bundle and produces a per-day forecast for a
single category over a horizon (<= 30 days). Because the model uses
autoregressive features (lag_7/14/30, rolling_7d/30d), prediction is **recursive**:
each predicted day is appended to the working history so the next day's lags and
rolling means are well defined. The confidence band is ``prediction ± 1.96 * RMSE``
using the per-category validation RMSE stored in the bundle.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import text

from config import (CONFIDENCE_Z, CURRENT_MODEL, HISTORY_LOOKBACK_DAYS,  # noqa: E402
                    HORIZON_MAX, get_engine)
from features import (FEATURE_COLUMNS, build_calendar_features)


def load_current() -> dict:
    if not CURRENT_MODEL.exists():
        raise FileNotFoundError("No promoted model found (ml/models/current.pkl). Train first.")
    return joblib.load(CURRENT_MODEL)


def _load_history(engine, category: str) -> pd.DataFrame:
    sql = text("""
        SELECT d.date AS date, SUM(f.quantity)::float AS units
        FROM gold.fact_sales f
        JOIN gold.dim_date d ON d.date_key = f.date_key
        JOIN gold.dim_product p ON p.product_key = f.product_key
        WHERE p.category = :cat
        GROUP BY d.date ORDER BY d.date
    """)
    return pd.read_sql(sql, engine, params={"cat": category})


def _load_calendar(engine) -> pd.DataFrame:
    return pd.read_sql(text(
        "SELECT event_name, event_type, start_date, end_date FROM oltp.calendar_events"), engine)


def predict(category: str, horizon: int = HORIZON_MAX, today: Optional[date] = None,
            bundle: Optional[dict] = None, engine=None) -> pd.DataFrame:
    """Return a DataFrame with columns ``date, prediction, lower, upper``."""
    horizon = max(1, min(int(horizon), HORIZON_MAX))
    bundle = bundle or load_current()
    engine = engine or get_engine()

    if category not in bundle["categories"]:
        raise ValueError(f"Unknown category '{category}'. Known: {bundle['categories']}")

    hist = _load_history(engine, category)
    calendar = _load_calendar(engine)
    if hist.empty:
        raise RuntimeError(f"No history for category '{category}'.")

    hist["date"] = pd.to_datetime(hist["date"])
    last_date = hist["date"].max().date()
    anchor = pd.Timestamp(today) if today is not None else pd.Timestamp(last_date) + pd.Timedelta(days=1)

    # Dense daily series of units up to the anchor (fill gaps with 0).
    idx = pd.date_range(hist["date"].min(), anchor - pd.Timedelta(days=1), freq="D")
    series = hist.set_index("date")["units"].reindex(idx, fill_value=0.0)

    cat_code = bundle["categories"].index(category)
    model = bundle["model"]
    rmse = bundle["rmse_per_category"].get(category, bundle.get("global_rmse", 1.0))

    forecast_dates = pd.date_range(anchor, periods=horizon, freq="D")
    cal_feats = build_calendar_features(forecast_dates, calendar).set_index("date")

    preds = []
    for d in forecast_dates:
        feat = {"category_code": cat_code}
        feat["lag_7"] = float(series.get(d - pd.Timedelta(days=7), 0.0))
        feat["lag_14"] = float(series.get(d - pd.Timedelta(days=14), 0.0))
        feat["lag_30"] = float(series.get(d - pd.Timedelta(days=30), 0.0))
        last7 = series.reindex(pd.date_range(d - pd.Timedelta(days=7), d - pd.Timedelta(days=1)))
        last30 = series.reindex(pd.date_range(d - pd.Timedelta(days=30), d - pd.Timedelta(days=1)))
        feat["rolling_7d"] = float(np.nan_to_num(last7.mean()))
        feat["rolling_30d"] = float(np.nan_to_num(last30.mean()))
        c = cal_feats.loc[d]
        for col in FEATURE_COLUMNS:
            if col not in feat:
                feat[col] = float(c[col])
        X = pd.DataFrame([[feat[col] for col in FEATURE_COLUMNS]], columns=FEATURE_COLUMNS)
        yhat = float(max(0.0, model.predict(X)[0]))
        series.loc[d] = yhat  # feed back for the next day's lags/rolling
        preds.append({
            "date": d.date().isoformat(),
            "prediction": round(yhat, 2),
            "lower": round(max(0.0, yhat - CONFIDENCE_Z * rmse), 2),
            "upper": round(yhat + CONFIDENCE_Z * rmse, 2),
        })

    return pd.DataFrame(preds)


if __name__ == "__main__":
    import sys
    cat = sys.argv[1] if len(sys.argv) > 1 else "Qamis"
    print(predict(cat, 30).to_string(index=False))
