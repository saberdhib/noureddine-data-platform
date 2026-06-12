# NOUREDDINE — Airflow orchestrator image (Bloc 3 + Bloc 4).
# Adds dbt (isolated venv) + ML/monitoring libraries so that BOTH
# ingest_orders.dbt_build (Bloc 3) and retrain_model/monitor_model (Bloc 4) can
# actually run inside the container — resolves the inherited audit gap §D.1.
FROM apache/airflow:2.9.1

USER root
# libgomp1 is required by lightgbm; curl for the healthcheck (already present).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# dbt in an ISOLATED venv so its pinned deps never fight Airflow's.
RUN python -m venv /opt/dbt-venv \
    && /opt/dbt-venv/bin/pip install --no-cache-dir \
        "dbt-core==1.8.2" "dbt-postgres==1.8.2" \
    && chown -R airflow: /opt/dbt-venv

USER airflow
# ML + monitoring libs into the Airflow env (PythonOperators import them in-process).
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir -r /tmp/requirements-airflow.txt

# The ingest_orders DAG invokes dbt via $DBT_BIN (set in compose to the venv).
ENV DBT_BIN=/opt/dbt-venv/bin/dbt
