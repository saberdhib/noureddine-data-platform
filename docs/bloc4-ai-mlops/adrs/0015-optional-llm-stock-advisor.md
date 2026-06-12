# ADR-0015 — Optional LLM stock advisor (outside the zero-licence baseline)

**Date:** 2026-06-12
**Status:** Accepted

## Context

The platform's core forecasting is a governed, zero-licence, explainable LightGBM
model (ADR-0009) served via FastAPI and consumed in Streamlit. The business need
is **stock piloting against Islamic-calendar demand**. Stakeholders asked for a
high-ROI, "wow", non-gadget AI feature. A natural-language layer that turns the
existing numbers into an **actionable restock decision** addresses the literal
business purpose — but a hosted LLM is a **paid SaaS** and an **external data
processor**, which the locked baseline forbids (zero-licence, DPIA #2).

## Decision

Add an **optional, isolated** "AI Restock Advisor" Streamlit page
(`pages/4_🤖_AI_Advisor.py` + `lib/ai_advisor.py`) that calls an OpenAI model to
produce a French restock briefing. It is **outside the zero-licence baseline** and
strictly opt-in:

- **Disabled by default.** Active only when `OPENAI_API_KEY` is set; otherwise the
  page shows the grounding data and a "configure the key" message. The rest of the
  platform is unchanged and remains 100% zero-licence.
- **Grounded, no hallucinated figures.** The model receives only the structured
  numbers we compute (forecast, inventory, days of cover, suggested reorder units,
  upcoming calendar events) and is instructed to invent nothing; reorder quantities
  are computed in code, not by the LLM.
- **No PII (DPIA #2).** Only **category-level aggregates** are sent — never a
  customer id, name, email or any individual field (`ai_advisor._assert_no_pii`).
- **Human-in-the-loop.** The advisor proposes; a human validates. It is decision
  support, never an automated ordering action.
- **Config via env**, never a hard-coded key: `OPENAI_API_KEY`, `OPENAI_MODEL`
  (default `gpt-4o-mini`).

## Consequences

- ✅ Real ROI: converts forecasts into a ready-to-act buyer briefing — the exact
  decision the platform exists to support.
- ✅ Coherence preserved: the **defensible PFE baseline stays zero-licence + SHAP**;
  this is a clearly-labelled bonus, not a dependency of any other component.
- ⚠️ Introduces a paid, external dependency **when enabled** — documented here and
  in the Bloc 4 README; not part of the certification's zero-cost guarantee.
- ⚠️ Cost/latency per call (mitigated by `gpt-4o-mini` + on-demand button, not
  auto-run).

## Alternatives considered

- **Improve the forecast with an LLM** — rejected: LLMs don't forecast tabular
  demand better than LightGBM and would forfeit SHAP explainability (ADR-0009).
- **Local open-source LLM (Ollama)** — keeps zero-licence but adds heavy runtime
  weight (GB of models, GPU) disproportionate for a laptop demo; viable future
  swap (the `ai_advisor` boundary is provider-agnostic).
- **Do nothing** — perfectly valid for the strict PFE submission; this ADR makes
  the feature an explicit, reversible option.
