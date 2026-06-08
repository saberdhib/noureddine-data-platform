# MinIO — Object Storage (Data Lake)

MinIO provides S3-compatible object storage running locally inside Docker.

## Buckets

| Bucket   | Medallion Layer | Purpose |
|----------|-----------------|---------|
| `bronze` | Bronze (raw)    | Raw ingested files: Shopify exports, marketing CSVs, RAG logs — unchanged from source |
| `silver` | Silver (clean)  | Cleaned, typed, quality-validated Parquet files produced by dbt (Bloc 3) |
| `gold`   | Gold (business) | Business-metric aggregates and ML-ready feature sets, ready for dashboarding and model training |

## AWS S3 Migration

MinIO uses the **same S3 API** as AWS S3. To migrate to the cloud:
1. Replace `MINIO_API_PORT` endpoint (`http://minio:9000`) with your S3 bucket URL.
2. Replace `MINIO_ROOT_USER/PASSWORD` with AWS IAM Access Key / Secret.
3. No application code changes required — the S3 client calls are identical.

## Console

Access the MinIO web console at: `http://localhost:9001` (or `MINIO_CONSOLE_PORT`)

Default credentials are in `.env` / `.env.example`.
