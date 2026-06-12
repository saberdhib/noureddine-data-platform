# NOUREDDINE — Bloc 4 FastAPI serving image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps for lightgbm (libgomp) + healthcheck (curl).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 curl && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt

# App code + the ML package (predict/features/config). models/ is mounted read-only.
COPY api/ /app/api/
COPY ml/src/ /app/ml/src/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=5 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--app-dir", "/app/api", "--host", "0.0.0.0", "--port", "8000"]
