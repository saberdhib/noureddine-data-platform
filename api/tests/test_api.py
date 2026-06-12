"""API tests with FastAPI TestClient.

A fake model bundle is injected (no DB, no real model file needed) so the test
runs fast and free in CI. Covers: open endpoints, auth enforcement, schema
validation, and bad input.
"""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
os.environ["API_KEY"] = "test-key"

import main  # noqa: E402

FAKE_BUNDLE = {
    "version": "test_v1", "trained_at": "2026-01-01T00:00:00+00:00",
    "categories": ["Qamis", "Grooming"], "feature_names": ["category_code", "lag_7"],
    "target": "units", "metrics": {"global": {"mape": 0.12}},
}


@pytest.fixture(autouse=True)
def patch_model(monkeypatch):
    monkeypatch.setattr(main, "_load_bundle", lambda: FAKE_BUNDLE)
    yield


@pytest.fixture
def client():
    return TestClient(main.app)


def test_health_open(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_model_info_open(client):
    r = client.get("/model-info")
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == "test_v1"
    assert body["global_mape"] == 0.12
    assert "Qamis" in body["categories"]


def test_predict_requires_key(client):
    r = client.post("/predict", json={"category": "Qamis", "horizon": 7})
    assert r.status_code == 401


def test_predict_with_key(client, monkeypatch):
    import pandas as pd
    fake = pd.DataFrame([{"date": "2026-06-12", "prediction": 10.0, "lower": 5.0, "upper": 15.0}])
    # Patch the lazily-imported predict function.
    import predict as predict_mod
    monkeypatch.setattr(predict_mod, "predict", lambda *a, **k: fake)

    r = client.post("/predict", json={"category": "Qamis", "horizon": 1},
                    headers={"X-API-Key": "test-key"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["category"] == "Qamis"
    assert len(body["forecast"]) == 1
    assert body["forecast"][0]["lower"] <= body["forecast"][0]["upper"]


def test_predict_unknown_category(client):
    r = client.post("/predict", json={"category": "Nope", "horizon": 7},
                    headers={"X-API-Key": "test-key"})
    assert r.status_code == 422


def test_predict_bad_horizon(client):
    r = client.post("/predict", json={"category": "Qamis", "horizon": 999},
                    headers={"X-API-Key": "test-key"})
    assert r.status_code == 422


def test_retrain_requires_key(client):
    r = client.post("/retrain")
    assert r.status_code == 401
