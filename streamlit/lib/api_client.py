"""Thin client for the FastAPI forecasting service (Bloc 4).

Streamlit gets ALL forecasts through this client — it never imports the model.
The API key is read from the ``API_KEY`` env var and sent as ``X-API-Key``.
"""
from __future__ import annotations

import os

import pandas as pd
import requests

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
API_KEY = os.getenv("API_KEY", "noureddine-dev-key")
TIMEOUT = 30


def _headers() -> dict:
    return {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def health() -> dict:
    r = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def model_info() -> dict:
    r = requests.get(f"{API_URL}/model-info", timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def predict(category: str, horizon: int = 30) -> pd.DataFrame:
    """Call POST /predict and return a DataFrame[date, prediction, lower, upper]."""
    r = requests.post(
        f"{API_URL}/predict", headers=_headers(),
        json={"category": category, "horizon": int(horizon)}, timeout=TIMEOUT,
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json()["forecast"])
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df
