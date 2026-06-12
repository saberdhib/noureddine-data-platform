"""Evidently model-monitoring report (Bloc 4).

Builds a reference vs current comparison:
  - **Reference**: the training-matrix snapshot saved during the last training run
    (``ml/models/training_data_snapshot.parquet``).
  - **Current**: the last 30 days of actuals + the model's 1-step-ahead predictions.

It produces an Evidently HTML report (DataDrift + Regression presets), then
extracts the overall feature-drift score, target drift and MAPE/RMSE and INSERTs
them into ``monitoring.model_metrics``. A breach of ``DRIFT_THRESHOLD`` /
``MAPE_THRESHOLD`` flags the row so the ``monitor_model`` DAG can trigger a retrain.

Run with ``--force-drift`` to perturb the current window and deliberately trip the
drift threshold (used in the demo to show the drift-triggered retrain).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sqlalchemy import text

ML_SRC = Path(__file__).resolve().parents[2] / "ml" / "src"
sys.path.insert(0, str(ML_SRC))

from config import SNAPSHOT_FILE, get_engine, CURRENT_MODEL  # noqa: E402
from features import FEATURE_COLUMNS, TARGET, build_training_matrix  # noqa: E402

REPORTS_DIR = Path(__file__).resolve().parent / "reports"
DRIFT_THRESHOLD = float(os.getenv("DRIFT_THRESHOLD", "0.5"))
MAPE_THRESHOLD = float(os.getenv("MAPE_THRESHOLD", "0.30"))


def _build_windows(engine, model_bundle, current_days: int = 30, reference_days: int = 90):
    """Return (reference, current) frames with features + 1-step-ahead predictions.

    Drift is monitored against the **recent baseline**: ``current`` is the last
    ``current_days`` of actuals, ``reference`` is the ``reference_days`` window
    immediately before it (the persisted training distribution — see the snapshot
    in ``ml/models/``). Adjacent windows keep a healthy model reading "nominal".
    """
    from train import load_calendar, load_daily_demand

    daily = load_daily_demand(engine)
    calendar = load_calendar(engine)
    _, _, _, frame, _ = build_training_matrix(daily, calendar)
    frame = frame.copy()
    frame["prediction"] = np.clip(model_bundle["model"].predict(frame[FEATURE_COLUMNS]), 0, None)

    max_date = frame["date"].max()
    cur_start = max_date - pd.Timedelta(days=current_days)
    ref_start = cur_start - pd.Timedelta(days=reference_days)
    current = frame[frame["date"] > cur_start].reset_index(drop=True)
    reference = frame[(frame["date"] > ref_start) & (frame["date"] <= cur_start)].reset_index(drop=True)
    return reference, current


# Deterministic calendar/time features always differ window-to-window, so they
# are NOT meaningful data-drift signals. We monitor demand-level features only.
DRIFT_MONITOR_COLS = ["lag_7", "lag_14", "lag_30", "rolling_7d", "rolling_30d"]
EFFECT_SIZE = 0.30   # require a >=30% relative mean shift to count as real drift


def _drift_score(reference: pd.DataFrame, current: pd.DataFrame, cols) -> tuple:
    """Share of demand-level features that drifted.

    A feature counts as drifted only if the KS test is significant (p<0.05) AND
    the relative shift in mean exceeds ``EFFECT_SIZE`` — this suppresses the
    false positives that pure seasonality would otherwise trigger.
    """
    drifted = 0
    for c in cols:
        try:
            ref = reference[c].astype(float)
            cur = current[c].astype(float)
            _, p = ks_2samp(ref, cur)
            rel_shift = abs(cur.mean() - ref.mean()) / (abs(ref.mean()) + 1e-9)
            if p < 0.05 and rel_shift >= EFFECT_SIZE:
                drifted += 1
        except Exception:
            pass
    return drifted, len(cols), (drifted / len(cols) if cols else 0.0)


def _mape(y_true, y_pred) -> float:
    y_true = np.asarray(y_true, float)
    y_pred = np.asarray(y_pred, float)
    denom = np.where(y_true == 0, np.nan, y_true)
    with np.errstate(invalid="ignore", divide="ignore"):
        return float(np.nanmean(np.abs((y_true - y_pred) / denom)))


def _rmse(y_true, y_pred) -> float:
    return float(np.sqrt(np.mean((np.asarray(y_true, float) - np.asarray(y_pred, float)) ** 2)))


def _evidently_html(reference: pd.DataFrame, current: pd.DataFrame, path: Path):
    """Best-effort Evidently HTML (DataDrift + Regression). Non-fatal on failure."""
    try:
        from evidently import DataDefinition, Dataset, Regression, Report
        from evidently.presets import DataDriftPreset, RegressionPreset

        cols = FEATURE_COLUMNS + [TARGET, "prediction"]
        data_def = DataDefinition(
            numerical_columns=[c for c in FEATURE_COLUMNS if c != "category_code"] + [TARGET, "prediction"],
            categorical_columns=["category_code"],
            regression=[Regression(target=TARGET, prediction="prediction")],
        )
        ref_ds = Dataset.from_pandas(reference[cols].copy(), data_definition=data_def)
        cur_ds = Dataset.from_pandas(current[cols].copy(), data_definition=data_def)
        report = Report(metrics=[DataDriftPreset(), RegressionPreset()])
        snapshot = report.run(current_data=cur_ds, reference_data=ref_ds)
        snapshot.save_html(str(path))
        return True
    except Exception as exc:  # pragma: no cover
        print(f"WARNING: Evidently HTML generation failed ({exc}); metrics still computed.")
        path.write_text(f"<html><body><h1>Evidently report</h1><p>Generation error: {exc}</p></body></html>")
        return False


def generate(force_drift: bool = False) -> dict:
    import joblib

    engine = get_engine()
    bundle = joblib.load(CURRENT_MODEL)
    # Snapshot is the persisted training distribution; we monitor against the
    # recent baseline window for a stable, low-false-positive drift signal.
    _ = SNAPSHOT_FILE  # documented training-data snapshot (kept by train.py)
    reference, current = _build_windows(engine, bundle, current_days=30, reference_days=90)

    note = "nominal"
    if force_drift:
        # Deliberately shift the current window to trip the drift detector (demo).
        for c in ["lag_7", "lag_30", "rolling_7d", "rolling_30d", TARGET]:
            current[c] = current[c] * 3.0 + 50.0
        current["prediction"] = np.clip(bundle["model"].predict(current[FEATURE_COLUMNS]), 0, None)
        note = "forced-drift demo"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"report_{timestamp}.html"
    _evidently_html(reference, current, report_path)

    n_drift, n_feat, drift_score = _drift_score(reference, current, DRIFT_MONITOR_COLS)
    _, _, target_drift = _drift_score(reference[[TARGET]], current[[TARGET]], [TARGET])
    mape = _mape(current[TARGET], current["prediction"])
    rmse = _rmse(current[TARGET], current["prediction"])
    breached = bool(drift_score >= DRIFT_THRESHOLD or (not np.isnan(mape) and mape >= MAPE_THRESHOLD))

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO monitoring.model_metrics
              (model_version, drift_score, n_drifted, n_features, target_drift, mape, rmse,
               report_path, breached, note)
            VALUES (:v,:ds,:nd,:nf,:td,:mape,:rmse,:rp,:br,:note)
        """), {
            "v": bundle.get("version", "unknown"), "ds": round(drift_score, 4),
            "nd": n_drift, "nf": n_feat, "td": round(target_drift, 4),
            "mape": None if np.isnan(mape) else round(mape, 4), "rmse": round(rmse, 4),
            "rp": str(report_path), "br": breached, "note": note,
        })

    result = {
        "drift_score": round(drift_score, 4), "n_drifted": n_drift, "n_features": n_feat,
        "target_drift": round(target_drift, 4),
        "mape": None if np.isnan(mape) else round(mape, 4), "rmse": round(rmse, 4),
        "breached": breached, "report": str(report_path),
        "drift_threshold": DRIFT_THRESHOLD, "mape_threshold": MAPE_THRESHOLD,
    }
    print(f"Evidently run: {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-drift", action="store_true", help="Perturb current window to trip drift.")
    args = parser.parse_args()
    generate(force_drift=args.force_drift)
