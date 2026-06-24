"""Airflow DAG: export_to_lake (Bloc 3) — materialise silver & gold into the lake.

dbt builds silver/gold INSIDE PostgreSQL (the warehouse). This DAG mirrors those
modelled layers into the MinIO data lake as Parquet, so the medallion is tangible
in object storage too (silver/gold buckets) — the lake/warehouse separation a real
S3 deployment would have. Each table/view -> s3://<schema>/<name>.parquet.

Heavy imports happen inside the task so the DAG parses even without boto3/pandas.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

POSTGRES_CONN_ID = "noureddine_postgres"
LAYERS = {"silver": "silver", "gold": "gold"}  # postgres schema -> MinIO bucket

DEFAULT_ARGS = {
    "owner": "noureddine",
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def _notify_failure(context):
    print(f"[ALERT] export_to_lake task failed: {context.get('task_instance')}")


def export_layers(**_):
    import io
    import os
    import uuid

    import pandas as pd
    from minio import Minio
    from airflow.providers.postgres.hooks.postgres import PostgresHook

    engine = PostgresHook(postgres_conn_id=POSTGRES_CONN_ID).get_sqlalchemy_engine()
    endpoint = os.environ.get("MINIO_ENDPOINT", "http://minio:9000").replace("http://", "").replace("https://", "")
    client = Minio(
        endpoint,
        access_key=os.environ.get("MINIO_ACCESS_KEY_ID", "minio_admin"),
        secret_key=os.environ.get("MINIO_SECRET_ACCESS_KEY", "change_me_minio"),
        secure=False,
    )

    total = 0
    for schema, bucket in LAYERS.items():
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        objects = pd.read_sql(
            f"""SELECT table_name FROM information_schema.tables
                WHERE table_schema = '{schema}' ORDER BY table_name""",
            engine,
        )["table_name"].tolist()

        for name in objects:
            df = pd.read_sql(f'SELECT * FROM {schema}."{name}"', engine)
            # Postgres UUID columns come back as uuid.UUID objects pyarrow can't infer;
            # stringify them (and any other stray objects) so Parquet serialisation works.
            for col in df.columns:
                if df[col].dtype == "object":
                    df[col] = df[col].map(
                        lambda v: str(v) if isinstance(v, uuid.UUID) else v)
            data = df.to_parquet(index=False, engine="pyarrow")
            buf = io.BytesIO(data)
            key = f"{name}.parquet"
            client.put_object(bucket, key, buf, length=len(data),
                              content_type="application/octet-stream")
            print(f"  s3://{bucket}/{key}  ({len(df):,} rows)")
            total += 1
    print(f"[export_to_lake] wrote {total} Parquet objects to the lake.")


with DAG(
    dag_id="export_to_lake",
    description="Mirror silver & gold from Postgres into the MinIO lake as Parquet (Bloc 3).",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2024, 1, 1),
    schedule_interval="@daily",
    catchup=False,
    tags=["bloc3", "lake", "minio"],
    on_failure_callback=_notify_failure,
) as dag:
    PythonOperator(
        task_id="export_silver_gold_to_minio",
        python_callable=export_layers,
    )
