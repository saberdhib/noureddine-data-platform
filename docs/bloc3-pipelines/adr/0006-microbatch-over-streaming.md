# ADR 0006 — Micro-batch over streaming

**Status:** Accepted  
**Date:** 2026-06-12  
**Deciders:** Student developer

## Context

Bloc 3 is titled "real-time pipelines". Two architectural options exist:

| Option | Tools | Cost | Complexity |
|--------|-------|------|-----------|
| Pure streaming | Kafka / Kinesis + Spark Streaming | High (managed infra) | High (stateful consumers, at-least-once semantics, schema registry) |
| **Micro-batch** | Airflow schedule + dbt build | Zero (open source, Docker) | Low (SQL transforms, familiar DAG model) |

## Decision

Implement **micro-batch** ingestion: Airflow DAG runs every 10 minutes, picks up new rows from `oltp`, runs `dbt build` (which materialises silver + gold), and writes run metadata.

A data simulator injects new orders continuously (`drip.py`, every N seconds) so the demo appears live without requiring a real streaming stack.

## Rationale

- NOUREDDINE is an ~€8–9M SME with ~20k orders/year ≈ 2–3 orders/hour. Sub-minute latency is not a business requirement. A 10-minute micro-batch lag is operationally invisible.
- Kafka/Kinesis would add ≥3 new services (broker, zookeeper, schema registry), licence cost, and significant operational complexity for near-zero business gain.
- The jury question "why no Kafka?" has a clear answer: the data volume and latency requirements do not justify the infrastructure cost.
- Airflow + dbt is already in the stack (Bloc 2); no new tools needed.

## Consequences

- Latency: max ~10 min from order creation to gold refresh. Acceptable for daily/weekly reporting.
- If NOUREDDINE scales to 100k+ orders/day, a streaming layer can be added without touching the warehouse schema.
- The simulator's `drip.py` and the `history` mode are sufficient to demonstrate a credible data pipeline for the PFE evaluation.
