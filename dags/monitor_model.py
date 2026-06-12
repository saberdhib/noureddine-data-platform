"""Airflow DAG: monitor_model (Bloc 4).

Daily Evidently monitoring with a drift-triggered retrain.
Flow:
    generate_evidently_report -> check_thresholds -> [branch]
        - breach     -> trigger_retrain (TriggerDagRunOperator -> retrain_model)
        - no breach  -> no_action

`check_thresholds` reads the latest row of ``monitoring.model_metrics`` and the
``DRIFT_THRESHOLD`` / ``MAPE_THRESHOLD`` env vars. Heavy imports are inside tasks
so the DAG parses cleanly on a minimal scheduler.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_SRC = REPO_ROOT / "ml" / "src"
MONITORING = REPO_ROOT / "monitoring" / "evidently"

DEFAULT_ARGS = {
    "owner": "noureddine-mlops",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def _notify_failure(context):
    print(f"[ALERT] monitor_model task failed: {context.get('task_instance')}")


def generate_evidently_report(**_):
    sys.path.insert(0, str(MONITORING))
    force = os.getenv("FORCE_DRIFT", "0") == "1"
    from generate_report import generate
    result = generate(force_drift=force)
    print(f"Evidently result: {result}")
    return result


def check_thresholds(**_):
    """Branch: return the downstream task id based on the latest metrics row."""
    sys.path.insert(0, str(ML_SRC))
    from sqlalchemy import text

    from config import get_engine
    drift_threshold = float(os.getenv("DRIFT_THRESHOLD", "0.5"))
    mape_threshold = float(os.getenv("MAPE_THRESHOLD", "0.30"))
    with get_engine().connect() as conn:
        row = conn.execute(text("""
            SELECT drift_score, mape, breached FROM monitoring.model_metrics
            ORDER BY measured_at DESC LIMIT 1
        """)).fetchone()
    if not row:
        print("No model_metrics rows yet — no action.")
        return "no_action"
    drift_score, mape, breached = float(row[0] or 0), row[1], row[2]
    breach = bool(breached) or drift_score >= drift_threshold or (mape is not None and float(mape) >= mape_threshold)
    print(f"drift={drift_score} mape={mape} breach={breach} (thr drift={drift_threshold}, mape={mape_threshold})")
    return "trigger_retrain" if breach else "no_action"


with DAG(
    dag_id="monitor_model",
    description="Daily Evidently drift/performance monitoring + drift-triggered retrain (Bloc 4).",
    default_args=DEFAULT_ARGS,
    schedule="0 1 * * *",          # daily 01:00
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["bloc4", "mlops", "monitoring"],
    on_failure_callback=_notify_failure,
) as dag:
    t_report = PythonOperator(task_id="generate_evidently_report", python_callable=generate_evidently_report)
    t_check = BranchPythonOperator(task_id="check_thresholds", python_callable=check_thresholds)
    t_trigger = TriggerDagRunOperator(
        task_id="trigger_retrain",
        trigger_dag_id="retrain_model",
        wait_for_completion=False,
        reset_dag_run=True,
    )
    t_noop = EmptyOperator(task_id="no_action")

    t_report >> t_check >> [t_trigger, t_noop]
