# ADR-0009 — LightGBM over Prophet for demand forecasting

**Date:** 2026-06-12
**Status:** Accepted

## Context

Bloc 4 forecasts **daily orders per category** at a granularity of **category × day**, horizon **30 days**. Demand is event-driven and highly non-linear around the Islamic cultural calendar (Ramadan, Eid al-Fitr, Eid al-Adha, Nikah season) and retail peaks (Black Friday, Summer Sale). The candidate model families were classical time-series (Prophet / SARIMA) and gradient-boosted trees (LightGBM).

We need a model that: handles sharp event-driven peaks, trains in seconds on a laptop (zero-licence, near-zero-cost constraint), is explainable for the DPIA #2 commitment, and is defensible in an RNCP oral defence.

## Decision

**LightGBM** (gradient-boosted decision trees) is the forecasting engine. The target is modelled as a supervised regression problem over engineered calendar, lag, and rolling features, with `category` passed as a native categorical feature.

## Consequences

- ✅ **Event peaks**: tree splits on `days_to_next_eid_fitr`, `in_ramadan`, `in_pre_eid_window`, etc. capture abrupt regime changes that an additive Prophet model smooths over.
- ✅ **Explainability**: SHAP global summary plot (`ml/models/shap_summary.png`) gives per-feature attribution, satisfying the DPIA #2 transparency commitment. Prophet's components are interpretable but coarser.
- ✅ **Speed / cost**: trains in seconds on a laptop; no GPU, no licence.
- ✅ **Multi-series**: one model covers all categories via the categorical feature; no per-category model zoo to maintain.
- ⚠️ **Feature engineering burden**: lags, rolling means, and calendar features must be built explicitly (Prophet would infer seasonality automatically). Mitigated by reusing the fixed Bloc 3 calendar windows — we never recompute Hijri dates.
- ⚠️ **Extrapolation**: trees do not extrapolate trend beyond the training range; acceptable for a 30-day horizon on a stable, profitable brand.

## Alternatives considered

- **Prophet** — easy seasonality, weak on sharp event spikes, fewer explainability hooks for the DPIA; rejected.
- **SARIMA / classical** — one model per category, brittle on irregular Hijri-shifting events, harder to maintain; rejected.
- **Deep learning (LSTM / Temporal Fusion Transformer)** — disproportionate data and compute for a 30-FTE PME; not laptop-friendly; rejected.
