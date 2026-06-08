# ADR-0005 — Medallion Bronze/Silver/Gold schemas inside PostgreSQL

**Date:** 2024-06-01  
**Status:** Accepted

## Context

The Medallion architecture typically uses a Data Lake (object storage) for Bronze/Silver files, with a warehouse for Gold aggregates. Should Bronze and Silver schemas exist in PostgreSQL, or only in MinIO?

## Decision

Implement **all four schemas (`oltp`, `bronze`, `silver`, `gold`) in PostgreSQL**, mirroring the MinIO bucket structure.

## Rationale

- **dbt** targets a PostgreSQL profile. Having `bronze` and `silver` schemas in Postgres allows dbt to materialise staging models directly without a separate file-read step.
- **Data quality tests** (Great Expectations, dbt tests) run SQL — they need the data in a database, not just in object files.
- **Unified querying:** a single `psql` or pgAdmin connection can query across all layers for debugging.
- **MinIO + PostgreSQL coexistence:** MinIO holds raw files (Parquet, CSV); PostgreSQL holds the structured/typed version. This is the standard Lambda-style pattern for batch platforms.

## Consequences

- ✅ dbt models work without a file parsing step.
- ✅ Data quality tests run natively in SQL.
- ✅ Single endpoint for all exploratory queries.
- ⚠️ Bronze schema in PostgreSQL may receive very wide, untyped staging tables — this is intentional and expected.
- ⚠️ At production scale, Bronze in PostgreSQL adds write load. Mitigation: use `UNLOGGED TABLE` for Bronze staging tables in Bloc 3.
