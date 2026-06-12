# ADR-0012 — Streamlit for the business-facing app

**Date:** 2026-06-12
**Status:** Accepted

## Context

Business users (the founder, ops, stock planning) need a decision-support surface to read KPIs, see the 30-day demand forecast with Islamic-calendar context, and act on restock signals. This must be **business-only** and distinct from the technical monitoring, which stays in Grafana (clear separation). It must be quick to build, interactive for the screencast, and call the FastAPI serving layer rather than the model directly.

## Decision

**Streamlit** delivers the business app, with three pages, using **Plotly** for interactive charts:
- **Page 1 — Executive Dashboard**: gold KPIs (revenue, orders, AOV, top categories, top channels), filterable date range.
- **Page 2 — Demand Forecast** ⭐: category × day chart, J-90 history + J+30 prediction with confidence interval, and **Islamic-calendar overlays drawn directly on the chart** — gold band for Ramadan, dashed line per Eid al-Fitr, distinct colour for Eid al-Adha, lighter band for Nikah season, marker for Black Friday. The signature view.
- **Page 3 — Stock Pilot**: per-category table — current inventory, predicted 30d demand, days of cover, restock signal (🟢 / 🟠 / 🔴 per env-configurable thresholds).

Forecasts come from **FastAPI** (`/predict`); a **read-only** Postgres connection serves gold KPIs, inventory, and `calendar_events`. The app lives in `streamlit/` with its own `Dockerfile` and `requirements.txt`.

## Consequences

- ✅ **Fast to build, interactive**: pure-Python, Plotly charts render well in the demo video.
- ✅ **Separation of concerns**: Streamlit never loads `current.pkl`; all predictions transit FastAPI (mirrors a real deployment).
- ✅ **Governance**: read-only DB connection + business-only scope keep it a decision-support tool with human-in-the-loop (no auto-actions), honouring DPIA #2.
- ✅ **Clear split**: business in Streamlit, ops/ML monitoring in Grafana — no overlap, no confusion at defence.
- ⚠️ **Not multi-tenant / no auth model** — acceptable for an internal single-brand tool; a real deployment would front it with SSO.

## Alternatives considered

- **Grafana dashboards for business too** — blurs the monitoring/business boundary and is weaker for narrative forecast overlays; rejected.
- **Custom React + Next.js front-end** — disproportionate effort for a PFE decision-support surface; rejected.
- **Dash / Panel** — comparable, but Streamlit is faster to author and more screencast-friendly; rejected.
