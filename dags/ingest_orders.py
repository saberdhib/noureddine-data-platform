"""
ingest_orders.py — NOUREDDINE micro-batch ingestion DAG (Bloc 3).

Schedule: every 10 minutes (micro-batch, ADR 0006 — NOT streaming).

Flow:
  1. check_new_data    — count orders created since the previous successful run
  2. dbt_build         — `dbt build` (run + test) to refresh silver/gold
  3. write_run_metadata— record the run in monitoring.pipeline_runs

Observability:
  - on_failure_callback logs a structured JSON alert and (optionally) POSTs it
    to ALERT_WEBHOOK_URL.
  - FORCE_FAILURE=1 makes dbt_build fail on purpose (for the demo screencast).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

POSTGRES_CONN_ID = os.environ.get("NOUREDDINE_PG_CONN_ID", "noureddine_postgres")
DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt/noureddine")
DBT_PROFILES_DIR = os.environ.get("DBT_PROFILES_DIR", "/opt/airflow/dbt/noureddine")
# dbt lives in an isolated venv in the airflow image (infra/airflow/Dockerfile);
# fall back to PATH `dbt` for local runs (audit §D.1 / Fix A).
DBT_BIN = os.environ.get("DBT_BIN", "dbt")
ALERT_WEBHOOK_URL = os.environ.get("ALERT_WEBHOOK_URL")
FORCE_FAILURE = os.environ.get("FORCE_FAILURE", "0") == "1"


def _get_hook() -> PostgresHook:
    return PostgresHook(postgres_conn_id=POSTGRES_CONN_ID)


def alert_on_failure(context) -> None:
    """Structured JSON alert; best-effort webhook POST."""
    ti = context.get("task_instance")
    payload = {
        "alert": "pipeline_failure",
        "dag_id": context["dag"].dag_id,
        "task_id": ti.task_id if ti else None,
        "run_id": context.get("run_id"),
        "execution_date": str(context.get("logical_date") or context.get("execution_date")),
        "exception": str(context.get("exception")),
        "ts": datetime.utcnow().isoformat(),
    }
    print("ALERT " + json.dumps(payload))
    if ALERT_WEBHOOK_URL:
        try:
            import urllib.request

            req = urllib.request.Request(
                ALERT_WEBHOOK_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            urllib.request.urlopen(req, timeout=5)  # noqa: S310
        except Exception as exc:  # noqa: BLE001
            print(f"[alert] webhook POST failed: {exc}")


def check_new_data(**context) -> int:
    """Count orders created since the previous run; push to XCom."""
    prev = context.get("prev_start_date_success")
    hook = _get_hook()
    if prev:
        sql = "SELECT COUNT(*) FROM oltp.orders WHERE created_at >= %s"
        rows = hook.get_first(sql, parameters=(prev,))
    else:
        rows = hook.get_first("SELECT COUNT(*) FROM oltp.orders")
    count = int(rows[0]) if rows else 0
    print(f"[check_new_data] {count} new orders since {prev}")
    context["ti"].xcom_push(key="rows_processed", value=count)
    return count


def write_run_metadata(**context) -> None:
    ti = context["ti"]
    rows_processed = ti.xcom_pull(task_ids="check_new_data", key="rows_processed") or 0
    hook = _get_hook()
    hook.run(
        """
        INSERT INTO monitoring.pipeline_runs
            (run_id, dag_id, status, rows_processed, started_at, ended_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (run_id) DO UPDATE
            SET status = EXCLUDED.status,
                rows_processed = EXCLUDED.rows_processed,
                ended_at = EXCLUDED.ended_at
        """,
        parameters=(
            context["run_id"],
            context["dag"].dag_id,
            "success",
            int(rows_processed),
            context.get("data_interval_start"),
            datetime.utcnow(),
        ),
    )
    print(f"[write_run_metadata] recorded run {context['run_id']} ({rows_processed} rows)")


default_args = {
    "owner": "noureddine",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
    "on_failure_callback": alert_on_failure,
}

with DAG(
    dag_id="ingest_orders",
    description="Micro-batch ingestion: OLTP -> dbt build (silver/gold) -> run metadata.",
    schedule="*/10 * * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    default_args=default_args,
    tags=["bloc3", "ingestion", "microbatch", "dbt"],
) as dag:

    t_check = PythonOperator(
        task_id="check_new_data",
        python_callable=check_new_data,
    )

    # Install packages (Elementary) then build silver/gold. Uses the isolated
    # dbt venv via $DBT_BIN; dbt mount is read-write so deps/target can be written.
    dbt_cmd = f"{DBT_BIN} deps --no-version-check && {DBT_BIN} build --no-version-check"
    if FORCE_FAILURE:
        # Intentional failure path for the demo screencast.
        dbt_cmd = "echo 'FORCE_FAILURE active — failing on purpose' && exit 1"

    t_dbt = BashOperator(
        task_id="dbt_build",
        bash_command=(
            f"cd {DBT_PROJECT_DIR} && "
            f"DBT_PROFILES_DIR={DBT_PROFILES_DIR} {dbt_cmd}"
        ),
    )

    t_meta = PythonOperator(
        task_id="write_run_metadata",
        python_callable=write_run_metadata,
        trigger_rule="all_done",
    )

    t_check >> t_dbt >> t_meta
