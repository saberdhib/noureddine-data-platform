# ADR-0004 — Airflow executor choice for Bloc 2 skeleton

**Date:** 2024-06-01  
**Status:** Accepted

## Context

Airflow supports multiple executors: SequentialExecutor (SQLite, single-threaded), LocalExecutor (PostgreSQL, multi-process), CeleryExecutor (distributed workers), KubernetesExecutor. For Bloc 2, Airflow is a **running skeleton only** — no DAG logic is needed.

## Decision

Use **LocalExecutor** with **PostgreSQL** as the metadata database.

The Airflow metadata DB is stored in the shared PostgreSQL instance as a separate `airflow` database, created automatically via the init script `00_create_airflow_db.sql`.

## Consequences

- ✅ LocalExecutor supports concurrent DAG runs (unlike SequentialExecutor), so the skeleton is production-closer.
- ✅ PostgreSQL is already in the stack — no extra database service.
- ✅ Webserver and scheduler run in the same container via a `bash -c` entrypoint, reducing container count for the skeleton phase.
- ⚠️ Single-container webserver+scheduler is not production-recommended (Airflow docs suggest separating them). This is acceptable for Bloc 2 skeleton; Bloc 3 will refactor if needed.
- ⚠️ The `AIRFLOW__CORE__FERNET_KEY` in `docker-compose.yml` is a static example key — must be rotated for any real deployment.
