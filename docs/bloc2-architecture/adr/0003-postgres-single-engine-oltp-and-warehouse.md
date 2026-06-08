# ADR-0003 — PostgreSQL as single engine for OLTP and analytical warehouse

**Date:** 2024-06-01  
**Status:** Accepted

## Context

A mature data platform typically separates the OLTP transactional database (row-oriented, high write throughput) from the analytical warehouse (column-oriented, read-heavy aggregations). Options include:
- Separate OLTP (PostgreSQL) + OLAP (ClickHouse, DuckDB, Redshift).
- Single engine with logical schema separation.

## Decision

Use **PostgreSQL 16** as the single engine, with logical schema separation:
- Schema `oltp`: normalised transactional tables.
- Schemas `bronze`, `silver`, `gold`: staging and analytical tables.

## Consequences

- ✅ Zero additional services: one PostgreSQL container for both workloads.
- ✅ pgAdmin provides a unified view of all schemas.
- ✅ dbt-postgres connects to both layers in a single profile.
- ✅ At the ~50–10k row seed/demo scale, PostgreSQL OLAP performance is entirely sufficient.
- ⚠️ At production scale (millions of order rows, complex aggregations), a columnar store (ClickHouse, DuckDB, BigQuery) would outperform PostgreSQL on aggregation queries. This is the natural migration trigger.
- ⚠️ The `gold` star schema is designed to be easily migrated to a columnar store — all FK relationships and column types are standard SQL.

**Migration path:** when fact_sales exceeds ~50M rows, migrate `gold` schema to ClickHouse or BigQuery. The dbt models require only a profile change.
