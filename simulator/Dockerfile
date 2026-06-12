# NOUREDDINE data simulator (Bloc 3) — single stateful catch-up process.
# Build context is the repo root (see infra/docker-compose.yml) so the code is
# importable as the `simulator` package for `python -m simulator.run`.
FROM python:3.11-slim
WORKDIR /app

COPY simulator/requirements.txt /app/simulator/requirements.txt
RUN pip install --no-cache-dir -r /app/simulator/requirements.txt

COPY simulator/ /app/simulator/

# Runs forever: bootstrap (first run) then catch up to NOW() every
# CATCH_UP_INTERVAL_SECONDS. No SIM_MODE — one source of truth.
CMD ["python", "-m", "simulator.run"]
