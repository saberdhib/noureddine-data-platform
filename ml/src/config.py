"""Shared configuration for the NOUREDDINE ML package (Bloc 4).

Centralises the database connection and the on-disk model layout so that
``train``, ``predict``, ``retrain`` and the monitoring code all agree on where
things live. No PII is ever read here — only aggregate ``gold`` tables and the
governed ``oltp.calendar_events`` windows.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# --- Paths -------------------------------------------------------------------
ML_DIR = Path(__file__).resolve().parents[1]          # repo/ml
MODELS_DIR = ML_DIR / "models"
CURRENT_MODEL = MODELS_DIR / "current.pkl"
METRICS_FILE = MODELS_DIR / "metrics.json"
SHAP_FILE = MODELS_DIR / "shap_summary.png"
SNAPSHOT_FILE = MODELS_DIR / "training_data_snapshot.parquet"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

# --- Database ----------------------------------------------------------------
def database_url() -> str:
    """Build a SQLAlchemy URL from env vars, with laptop-friendly defaults.

    ``DATABASE_URL`` wins if set; otherwise we assemble it from the documented
    ``POSTGRES_*`` variables (see ``.env.example``).
    """
    explicit = os.getenv("DATABASE_URL")
    if explicit:
        return explicit
    user = os.getenv("POSTGRES_USER", "noureddine_user")
    password = os.getenv("POSTGRES_PASSWORD", "change_me_postgres")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "noureddine")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def get_engine() -> Engine:
    return create_engine(database_url(), pool_pre_ping=True)


# --- Model / forecasting constants ------------------------------------------
HORIZON_MAX = 30
VALIDATION_DAYS = 30
HISTORY_LOOKBACK_DAYS = 400        # how much history we pull for lag/rolling
CONFIDENCE_Z = 1.96                # ~95% interval from per-category RMSE
PROMOTION_TOLERANCE = 1.05         # promote if new_mape <= current_mape * 1.05
KEEP_VERSIONS = 5
