# ADR-0014 — Synthetic warehouse fixture as a stand-in for Bloc 3 output

**Date:** 2026-06-12
**Status:** Accepted

## Context

Bloc 4 consumes `gold.fact_sales` produced upstream by the Bloc 3 pipeline
(simulator → Airflow → dbt → star schema). The model needs a multi-year daily
demand history (category × day) to learn calendar-driven seasonality.

When the Bloc 4 build began, the working repository contained the Bloc 2 physical
model (schemas, tables, seed of ~50 rows/table) but **not** a populated, multi-year
`gold.fact_sales` history — there was not yet enough data to train on. The pre-flight
check (`SELECT count(*) FROM gold.fact_sales > 0`, ≥ 2 years of history) could not be
satisfied from the seed alone, and "do not train on no data" is a hard rule.

## Decision

Add a small, clearly-labelled **synthetic warehouse fixture generator**,
`ml/scripts/generate_demo_data.py`, that populates `oltp.calendar_events`,
`oltp.products/categories/inventory` and the `gold` star schema (`dim_*`,
`fact_sales`) with ~3 years of **obviously fake**, calendar-correlated daily demand
(Ramadan / pre-Eid / Eid al-Adha / Nikah / Black Friday / Summer Sale uplifts).

This is a **stand-in for the Bloc 3 output**, used only to make the ML pipeline
trainable and demoable. It is **not** wired into the Docker `init` scripts, so the
canonical `docker compose up` still loads the Bloc 2 seed and passes the Bloc 2/3
health checks; the fixture is an explicit, documented step in the Bloc 4 demo.

## Consequences

- ✅ The model trains end-to-end with realistic seasonal signal (global MAPE ≈ 11%),
  and every downstream component (API, Streamlit, Evidently, retrain) is verifiable.
- ✅ Governance respected: synthetic data only, no PII, no real personal data.
- ✅ Reversible: when the real Bloc 3 pipeline lands, drop the fixture step — the ML
  code reads `gold.fact_sales` unchanged, regardless of who populated it.
- ⚠️ The fixture reshapes `oltp.products/categories` for a clean category set, so it
  should be run on a demo database, not over a production-like Bloc 3 dataset.

## Alternatives considered

- **Wait for / re-run the Bloc 3 simulator** — out of scope for Bloc 4 and not present
  in the handed-over repo; rejected (would block the graded Bloc 4 deliverable).
- **Hand-write a few hundred rows of SQL seed** — insufficient history for lag/rolling
  features and seasonal learning; rejected.
- **Train on the 50-row Bloc 2 seed** — violates "do not train on no data"; rejected.
