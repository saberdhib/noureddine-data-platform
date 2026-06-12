# `api/` — FastAPI Model Serving (Bloc 4)

Serves the LightGBM demand forecaster. Owns the model; Streamlit calls this API
and never imports the model directly (separation of concerns).

```
api/
├── main.py          # FastAPI app + endpoints
├── auth.py          # X-API-Key dependency (governance P-03)
├── schemas.py       # Pydantic request/response models
├── Dockerfile       # slim image, mounts ml/models read-only
├── tests/           # TestClient tests (mocked model, no DB)
└── requirements.txt
```

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET  | `/health`     | open | liveness + model presence |
| GET  | `/model-info` | open | version, training date, global MAPE, feature list |
| POST | `/predict`    | **X-API-Key** | 1–30 day forecast for a category |
| POST | `/retrain`    | **X-API-Key** | fire-and-forget retraining job (202) |
| GET  | `/docs`       | open | OpenAPI / Swagger UI |

## Run

```bash
pip install -r api/requirements.txt
export POSTGRES_HOST=localhost POSTGRES_USER=noureddine_user POSTGRES_PASSWORD=... POSTGRES_DB=noureddine
export API_KEY=noureddine-dev-key
uvicorn main:app --app-dir api --port 8000

curl -s localhost:8000/health
curl -s -X POST localhost:8000/predict -H "X-API-Key: noureddine-dev-key" \
     -H "Content-Type: application/json" -d '{"category":"Qamis","horizon":30}'
```

In Docker the service is reachable as `http://api:8000` on the `noureddine_net`
network; the promoted model is mounted read-only at `/app/ml/models`.
