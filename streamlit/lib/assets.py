"""Brand asset access (Bloc 4) — read marketing media from the MinIO 'brand' bucket.

A light Digital Asset Manager: the brand/marketing media (logo, campaign visuals,
product & accessory shots) live in object storage (MinIO), read-only from Streamlit.
No customer data — marketing content only.
"""
from __future__ import annotations

import os

BUCKET = os.getenv("BRAND_BUCKET", "brand")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")


def _client():
    from minio import Minio
    ep = os.getenv("MINIO_ENDPOINT", "http://minio:9000").replace("http://", "").replace("https://", "")
    return Minio(
        ep,
        access_key=os.getenv("MINIO_ACCESS_KEY_ID", "minio_admin"),
        secret_key=os.getenv("MINIO_SECRET_ACCESS_KEY", "change_me_minio"),
        secure=False,
    )


def list_images(bucket: str = BUCKET) -> list[str]:
    c = _client()
    if not c.bucket_exists(bucket):
        return []
    return sorted(
        o.object_name for o in c.list_objects(bucket, recursive=True)
        if o.object_name.lower().endswith(IMAGE_EXT)
    )


def get_object(name: str, bucket: str = BUCKET) -> bytes:
    resp = _client().get_object(bucket, name)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()
