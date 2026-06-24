"""Page 2 — Demand Forecast ⭐ (Bloc 4).

J-90 history + J+30 forecast (with confidence band) per category, with Islamic
calendar overlays drawn directly on the chart. Forecasts come from the FastAPI
service (never the model directly).
"""
import json

import plotly.graph_objects as go
import streamlit as st

from lib import api_client, calendar_overlays, db, insights, llm

st.set_page_config(page_title="Demand Forecast", page_icon="📈", layout="wide")
st.title("📈 Demand Forecast")
st.caption("J-90 history + J+30 forecast with confidence band and Islamic-calendar overlays.")

# --- sidebar controls ---
cats = db.categories()
if not cats:
    st.error("No categories found in gold.dim_product.")
    st.stop()

# default to highest-volume category
top = db.top_categories("2023-01-01", "2026-12-31")
default_cat = top.iloc[0]["category"] if not top.empty else cats[0]
with st.sidebar:
    st.header("Controls")
    category = st.selectbox("Category", cats, index=cats.index(default_cat) if default_cat in cats else 0)
    horizon = st.slider("Forecast horizon (days)", 7, 30, 30)

# --- data ---
try:
    fc = api_client.predict(category, horizon)
except Exception as exc:
    st.error(f"Forecast API not reachable: {exc}")
    st.stop()

hist = db.category_history(category, days=90).sort_values("date")

# --- chart ---
fig = go.Figure()
fig.add_trace(go.Scatter(x=hist["date"], y=hist["units"], name="History (J-90)",
                         mode="lines", line=dict(color="#1f77b4")))
fig.add_trace(go.Scatter(x=fc["date"], y=fc["upper"], name="Upper", mode="lines",
                         line=dict(width=0), showlegend=False))
fig.add_trace(go.Scatter(x=fc["date"], y=fc["lower"], name="Confidence band", mode="lines",
                         line=dict(width=0), fill="tonexty", fillcolor="rgba(255,127,14,0.2)"))
fig.add_trace(go.Scatter(x=fc["date"], y=fc["prediction"], name="Forecast (J+30)",
                         mode="lines", line=dict(color="#ff7f0e", dash="dot")))

# calendar overlays across the full visible range
if not hist.empty:
    x_start = hist["date"].min()
else:
    x_start = fc["date"].min()
x_end = fc["date"].max()
calendar_overlays.apply_overlays(fig, db.calendar_events(), x_start, x_end)

fig.update_layout(height=480, margin=dict(l=10, r=10, t=30, b=10),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02),
                  yaxis_title="Units / day", xaxis_title="")
st.plotly_chart(fig, use_container_width=True)

st.caption("🟡 Ramadan band · 🔴 Eid al-Fitr · 🟢 Eid al-Adha · 🟣 Nikah season · ⬛ Black Friday")

# --- table + explainability ---
left, right = st.columns([2, 1])
with left:
    st.subheader("Predicted values")
    st.dataframe(fc, use_container_width=True, hide_index=True)
with right:
    with st.expander("What does the model see?", expanded=True):
        try:
            info = api_client.model_info()
            st.write("**Top feature families** (global SHAP):")
            st.markdown(
                "- Calendar proximity (`days_to_*`, `in_ramadan`, `in_pre_eid_window`)\n"
                "- Recent demand (`lag_7/14/30`, `rolling_7d/30d`)\n"
                "- Category + weekly seasonality"
            )
            st.caption(f"Model version: {info.get('version', '—')} · "
                       f"Global MAPE: {info.get('global_mape', '—')}")
            st.caption("See ml/models/shap_summary.png for the full SHAP summary plot.")
        except Exception:
            st.caption("Model info unavailable.")

# --- AI commentary on the forecast (optional LLM layer; aggregates only) --------
st.divider()
st.subheader("🪄 Commentaire IA sur la prévision")
if not llm.is_enabled():
    st.info("🔑 Active la clé LLM (`OPENAI_API_KEY` dans `.env`) pour un commentaire automatique.")
else:
    st.caption(f"Modèle : `{llm.OPENAI_MODEL}` · catégorie **{category}** · aucune PII.")
    if st.button("Commenter cette prévision", type="primary"):
        with st.spinner("Lecture de la courbe…"):
            try:
                snap = insights.forecast_snapshot(category, db.data_today(), horizon)
                sys = (
                    "Tu es analyste demande pour NOUREDDINE, marque e-commerce premium de mode "
                    "masculine dont la demande suit le calendrier islamique (Ramadan, Aïd al-Fitr, "
                    "Aïd al-Adha, saison des mariages) et les pics retail (Black Friday). À partir "
                    "UNIQUEMENT des chiffres agrégés fournis pour la catégorie, explique en français "
                    "et en 3-5 phrases : la tendance (historique 30j vs prévision), l'effet des "
                    "événements calendaires dans l'horizon, et une recommandation opérationnelle. "
                    "N'invente aucun chiffre."
                )
                st.markdown(llm.chat(sys, json.dumps(snap, ensure_ascii=False)))
            except Exception as exc:
                st.error(f"Échec de l'appel au modèle : {exc}")
