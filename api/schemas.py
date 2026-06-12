"""Pydantic schemas for the NOUREDDINE forecasting API (Bloc 4)."""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class PredictRequest(BaseModel):
    category: str = Field(..., examples=["Qamis"], description="Product category to forecast.")
    horizon: int = Field(30, ge=1, le=30, description="Number of days to forecast (1–30).")

    model_config = {"json_schema_extra": {"examples": [{"category": "Qamis", "horizon": 30}]}}


class ForecastPoint(BaseModel):
    date: str
    prediction: float
    lower: float
    upper: float


class PredictResponse(BaseModel):
    category: str
    horizon: int
    model_version: str
    generated_at: str
    forecast: List[ForecastPoint]


class ModelInfo(BaseModel):
    version: str
    trained_at: Optional[str] = None
    global_mape: Optional[float] = None
    categories: List[str] = []
    feature_names: List[str] = []
    target: Optional[str] = None


class RetrainResponse(BaseModel):
    status: str
    job_id: str
    message: str
