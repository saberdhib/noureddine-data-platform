# ADR-0010 — FastAPI for model serving

**Date:** 2026-06-12
**Status:** Accepted

## Context

The promoted LightGBM model must be served behind a network boundary so that consumers (the Streamlit business app, and any future client) obtain predictions through a stable contract rather than loading the model in-process. The serving layer must enforce the separation-of-concerns principle (architecture principle 5) and respect the governance auth spirit of policy P-03.

## Decision

**FastAPI** serves the model on internal port 8000, as a Docker Compose service with its own `Dockerfile` and `requirements.txt`.

Endpoints:
- `/health` and `/model-info` — open (liveness + active model metadata).
- `/predict` (POST: `category`, `horizon ≤ 30`) → list of `{date, prediction, lower, upper}` — **requires** `X-API-Key`.
- `/retrain` (POST, admin) → enqueues retraining — **requires** `X-API-Key`.

Auth is an API key read from an env var, passed in the `X-API-Key` header. OpenAPI docs are auto-published at `/docs`.

## Consequences

- ✅ **Contract-first**: auto-generated OpenAPI schema and `/docs` make the API self-documenting and screencast-friendly.
- ✅ **Separation of concerns**: Streamlit calls the API and **never** loads `current.pkl` directly — the same boundary a real deployment would have.
- ✅ **Governance**: `X-API-Key` on protected endpoints realises the P-03 access-control spirit; secret stays in `.env`, documented in `.env.example`.
- ✅ **Performance**: async ASGI server handles the low-concurrency PME load comfortably; Pydantic validates `horizon ≤ 30` at the edge.
- ⚠️ **Single shared key** (no per-user identity) — acceptable for an internal decision-support tool; a real deployment would add OAuth2 / per-client keys.

## Alternatives considered

- **Flask** — viable but no native async, no built-in OpenAPI/validation; rejected for ergonomics.
- **Streamlit loads the model directly** — violates separation of concerns and mirrors no real deployment; explicitly forbidden in Bloc 4 scope.
- **BentoML / MLflow serving** — heavier runtime and more moving parts than a 30-FTE PME needs; rejected as disproportionate.
