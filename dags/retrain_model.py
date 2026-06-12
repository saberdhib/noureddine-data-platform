"""Airflow DAG: retrain_model (Bloc 4).

Weekly scheduled retraining with a validation gate and atomic promotion.
Flow:
    check_upstream_quality  -> extract_training_data -> train_and_validate
    -> update_model_card     -> write_retrain_metadata

`train_and_validate` calls ``ml/src/retrain.py`` (extract -> features -> train ->
validate on held-out 30d -> promote IF new_mape <= current_mape * 1.05 ELSE hold).
Promotion is atomic (symlink swap). Heavy imports happen inside tasks so the DAG
parses cleanly even when ML deps are absent on the scheduler.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"

DEFAULT_ARGS = {
    "owner": "noureddine-mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _notify_failure(context):
    """on_failure_callback — mirrors the Bloc 3 pattern (log to monitoring)."""
    print(f"[ALERT] retrain_model task failed: {context.get('task_instance')}")


def check_upstream_quality(**_):
    """P-04 gate: refuse to train if the last Bloc 3 pipeline run failed."""
    sys.path.insert(0, str(ML_SRC))
    from sqlalchemy import text

    from config import get_engine
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT status FROM monitoring.pipeline_runs ORDER BY run_at DESC LIMIT 1"
        )).fetchone()
    status = row[0] if row else "unknown"
    print(f"Latest upstream pipeline status: {status}")
    if status == "failed":
        raise RuntimeError("Upstream data-quality run failed — aborting retrain (P-04 gate).")
    return status


def extract_training_data(**_):
    """Sanity-check that gold.fact_sales has rows before training."""
    sys.path.insert(0, str(ML_SRC))
    from sqlalchemy import text

    from config import get_engine
    with get_engine().connect() as conn:
        n = conn.execute(text("SELECT count(*) FROM gold.fact_sales")).scalar()
    print(f"gold.fact_sales rows available: {n}")
    if not n:
        raise RuntimeError("No training data in gold.fact_sales.")
    return int(n)


def train_and_validate(**_):
    sys.path.insert(0, str(ML_SRC))
    from retrain import retrain
    decision = retrain()
    # Log the promotion decision for Grafana annotation.
    from sqlalchemy import text

    from config import get_engine
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO monitoring.retrain_events
              (model_version, current_mape, new_mape, promoted, reason)
            VALUES (:v,:cm,:nm,:p,:r)
        """), {"v": decision.get("candidate_version"), "cm": decision.get("current_mape"),
               "nm": decision.get("new_mape"), "p": decision.get("promoted"),
               "r": decision.get("reason")})
    return decision


def update_model_card(**_):
    sys.path.insert(0, str(ML_SRC))
    from model_card import main as build_card
    build_card()


def write_retrain_metadata(**_):
    print("retrain_model run complete.")


with DAG(
    dag_id="retrain_model",
    description="Weekly LightGBM retraining with validation gate + atomic promotion (Bloc 4).",
    default_args=DEFAULT_ARGS,
    schedule="0 2 * * 0",          # Sundays 02:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["bloc4", "mlops", "retrain"],
    on_failure_callback=_notify_failure,
) as dag:
    t_quality = PythonOperator(task_id="check_upstream_quality", python_callable=check_upstream_quality)
    t_extract = PythonOperator(task_id="extract_training_data", python_callable=extract_training_data)
    t_train = PythonOperator(task_id="train_and_validate", python_callable=train_and_validate)
    t_card = PythonOperator(task_id="update_model_card", python_callable=update_model_card)
    t_meta = PythonOperator(task_id="write_retrain_metadata", python_callable=write_retrain_metadata)

    t_quality >> t_extract >> t_train >> t_card >> t_meta
