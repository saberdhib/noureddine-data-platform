# ADR 0007 — Elementary for data quality reporting

**Status:** Accepted  
**Date:** 2026-06-12  
**Deciders:** Student developer

## Context

dbt provides generic tests (`not_null`, `unique`, `accepted_values`, `relationships`) and custom singular tests. These tests pass/fail at build time but produce no persistent, browsable quality report.

The Bloc 3 consigne requires a "data-quality" layer with anomaly detection and a visible report.

## Options

| Tool | Description | Cost | Integration |
|------|-------------|------|------------|
| **Elementary** | dbt package — uploads test results as dbt artifacts; `edr report` generates an HTML report | Free/open source | Native dbt package |
| Great Expectations | Standalone Python framework | Free | Requires separate runner |
| Monte Carlo / Soda | SaaS anomaly detection | Paid | External |

## Decision

Use **Elementary** (`elementary-data/elementary`, pinned to 0.14.x).

Configuration in `dbt_project.yml`:
```yaml
on-run-end:
  - "{{ elementary.upload_dbt_artifacts() }}"
```

This uploads dbt run/test artifacts into the `elementary` schema after every `dbt build`.
The HTML report is generated with:
```bash
edr report --profiles-dir /path/to/profiles --project-dir /path/to/project
```

## Rationale

- Zero additional infrastructure — Elementary runs as a dbt package and writes to the same Postgres.
- The HTML report is the de-facto standard for dbt-native data quality demonstration in 2025/2026.
- The jury can open `elementary_report.html` to see test pass-rates, anomaly trends, and model freshness.
- Tight integration: Elementary reads dbt run results directly; no ETL glue code.

## Consequences

- Elementary adds ~5s to every `dbt build` (artifact upload). Acceptable for a 10-minute batch.
- The report requires `edr` CLI to be installed (added to the Airflow container or run manually).
- Elementary's anomaly detection requires a history of runs; the report improves over time.
