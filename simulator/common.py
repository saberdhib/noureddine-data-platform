"""
Shared helpers for the NOUREDDINE data simulator:
- env-driven connections (Postgres via SQLAlchemy, MinIO/S3 via boto3)
- reference data (categories, channels)
- product catalogue helpers
"""
import os
import json
import uuid
from datetime import date, datetime

import boto3
from botocore.client import Config
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Connection config (all from env, with laptop-friendly defaults)
# ---------------------------------------------------------------------------
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://noureddine_user:change_me_postgres@postgres:5432/noureddine",
)
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY_ID", "minio_admin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_ACCESS_KEY", "change_me_minio")
BRONZE_BUCKET = os.environ.get("BRONZE_BUCKET", "bronze")

CATEGORIES = [
    ("Qamis", "traditional_wear"),
    ("Grooming", "grooming"),
    ("ReadyToWear", "ready_to_wear"),
    ("Suit", "formal"),
    ("Accessory", "accessories"),
    ("LeatherGoods", "leather"),
    ("GiftSet", "gifts"),
]

CHANNELS = [
    "instagram", "tiktok", "affiliate", "paid_ads",
    "qr_code", "web_search", "ai_search", "direct",
]

# typical price band per category (eur)
CATEGORY_PRICE_BAND = {
    "Qamis": (60, 250),
    "Grooming": (20, 60),
    "ReadyToWear": (45, 200),
    "Suit": (180, 450),
    "Accessory": (15, 90),
    "LeatherGoods": (50, 220),
    "GiftSet": (70, 300),
}

BUSINESS_TABLES = [
    "order_items", "shipments", "marketing_events", "rag_conversations",
    "orders", "inventory", "products", "customers",
]


def get_engine():
    return create_engine(DB_URL, future=True)


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _json_default(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, uuid.UUID):
        return str(o)
    return str(o)


def put_bronze(s3, key: str, payload) -> None:
    """Dump a raw JSON object to the bronze bucket. Best-effort (never blocks DB writes)."""
    try:
        s3.put_object(
            Bucket=BRONZE_BUCKET,
            Key=key,
            Body=json.dumps(payload, default=_json_default).encode("utf-8"),
            ContentType="application/json",
        )
    except Exception as exc:  # noqa: BLE001 - bronze dump is best-effort
        print(f"[warn] bronze put failed for {key}: {exc}")


def ensure_bucket(s3) -> None:
    try:
        s3.head_bucket(Bucket=BRONZE_BUCKET)
    except Exception:
        try:
            s3.create_bucket(Bucket=BRONZE_BUCKET)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] could not ensure bucket {BRONZE_BUCKET}: {exc}")
