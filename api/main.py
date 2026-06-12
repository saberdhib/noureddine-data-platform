"""FastAPI serving layer for the NOUREDDINE demand forecaster (Bloc 4).

Endpoints:
  GET  /health      open   -> liveness
  GET  /model-info  open   -> version, training date, global MAPE, feature list
  POST /predict     auth   -> 30-day (or shorter) forecast for a category
  POST /retrain     auth   -> fire-and-forget retraining job

Separation of concerns: this service owns the model; Streamlit must call this API
and never import the model directly. Auth via X-API-Key on protected endpoints.
"""
from __future__ import annotations

import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
from fastapi import Depends, FastAPI, HTTPException

# Make the ML package importable (mounted at /app/ml in the container).
ML_SRC = Path(__file__).resolve().parents[1] / "ml" / "src"
sys.path.insert(0, str(ML_SRC))

from auth import require_api_key  # noqa: E402
from schemas import (ModelInfo, PredictRequest, PredictResponse,  # noqa: E402
                     RetrainResponse)

CURRENT_MODEL = ML_SRC.parent / "models" / "current.pkl"
RETRAIN_LOG_DIR = ML_SRC.parent / "models" / "retrain_jobs"

app = FastAPI(
    title="NOUREDDINE Demand Forecast API",
    description="Serves daily per-category demand forecasts (LightGBM). Bloc 4 — AI/MLOps.",
    version="1.0.0",
    openapi_tags=[
        {"name": "health", "description": "Liveness & model metadata (open)."},
        {"name": "forecast", "description": "Demand forecasting (requires X-API-Key)."},
        {"name": "ops", "description": "Operational / admin actions (requires X-API-Key)."},
    ],
)


def _load_bundle() -> dict:
    if not CURRENT_MODEL.exists():
        raise HTTPException(status_code=503, detail="No model is currently promoted. Train first.")
    return joblib.load(CURRENT_MODEL)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok", "model_present": CURRENT_MODEL.exists()}


@app.get("/model-info", response_model=ModelInfo, tags=["health"])
def model_info():
    bundle = _load_bundle()
    return ModelInfo(
        version=bundle.get("version", "unknown"),
        trained_at=bundle.get("trained_at"),
        global_mape=bundle.get("metrics", {}).get("global", {}).get("mape"),
        categories=bundle.get("categories", []),
        feature_names=bundle.get("feature_names", []),
        target=bundle.get("target"),
    )


@app.post("/predict", response_model=PredictResponse, tags=["forecast"])
def predict_endpoint(req: PredictRequest, _: str = Depends(require_api_key)):
    from predict import predict as run_predict  # imported lazily (needs DB)

    bundle = _load_bundle()
    if req.category not in bundle.get("categories", []):
        raise HTTPException(
            status_code=422,
            detail=f"Unknown category '{req.category}'. Known: {bundle.get('categories', [])}",
        )
    try:
        df = run_predict(req.category, req.horizon, bundle=bundle)
    except Exception as exc:  # pragma: no cover - surfaced as 500 with context
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}")

    return PredictResponse(
        category=req.category, horizon=req.horizon,
        model_version=bundle.get("version", "unknown"),
        generated_at=datetime.now(timezone.utc).isoformat(),
        forecast=df.to_dict(orient="records"),
    )


@app.post("/retrain", response_model=RetrainResponse, status_code=202, tags=["ops"])
def retrain_endpoint(_: str = Depends(require_api_key)):
    """Fire-and-forget retraining job (admin). Logs to ml/models/retrain_jobs/."""
    job_id = uuid.uuid4().hex[:12]
    RETRAIN_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = RETRAIN_LOG_DIR / f"{job_id}.log"
    env = dict(os.environ)
    with open(log_path, "w") as log:
        subprocess.Popen(
            [sys.executable, str(ML_SRC / "retrain.py")],
            stdout=log, stderr=subprocess.STDOUT, env=env, cwd=str(ML_SRC),
        )
    return RetrainResponse(
        status="accepted", job_id=job_id,
        message=f"Retraining started. Log: ml/models/retrain_jobs/{job_id}.log",
    )
