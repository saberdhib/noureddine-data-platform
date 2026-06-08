# ADR-0001 — MinIO over AWS S3 for object storage

**Date:** 2024-06-01  
**Status:** Accepted

## Context

The platform needs S3-compatible object storage for the Data Lake (Bronze/Silver/Gold buckets). The canonical solution is AWS S3, but the PFE constraint requires **zero external cloud cost** and **full laptop reproducibility**.

## Decision

Use **MinIO** (self-hosted, Docker-deployed) as the S3-compatible object store.

MinIO exposes the full S3 REST API. All application code (dbt, Airflow, future ML pipeline) uses the S3 client library (`boto3` / `s3fs`) with only the endpoint URL configured differently.

## Consequences

- ✅ Zero cost, runs entirely in Docker.
- ✅ `docker compose up` reproduces the full environment in one command.
- ✅ S3-native API: migration to AWS S3 requires only endpoint + credential changes.
- ✅ MinIO console provides a visual bucket browser.
- ⚠️ Not suitable for production at scale (no multi-tenant IAM, limited throughput vs S3).
- ⚠️ AGPL-3.0 licence: commercial use requires checking licence compatibility.

**Migration path to AWS S3:** documented in `infra/minio/README.md`.
